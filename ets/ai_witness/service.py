"""AI Witness session chaining, signing, verification, and ETS projection."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ets.ai_witness.models import AIWitnessEvent, SignedWitnessRecord
from ets.core.api import EvidenceEvent, canonical_sha256, canonicalize


class WitnessValidationError(ValueError):
    """Raised when a witness record violates session or signature invariants."""


class AIWitnessLedger:
    """In-memory reference witness with per-session hash chaining and Ed25519 attestations."""

    def __init__(self, *, witness_id: str, signing_key_id: str, private_key_hex: str):
        if not witness_id or len(witness_id) > 128:
            raise WitnessValidationError("witness_id must contain 1-128 characters")
        if not signing_key_id or len(signing_key_id) > 256:
            raise WitnessValidationError("signing_key_id must contain 1-256 characters")
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except ValueError as exc:
            raise WitnessValidationError("private key must be a 32-byte Ed25519 key") from exc
        self.witness_id = witness_id
        self.signing_key_id = signing_key_id
        self._session_heads: dict[str, tuple[int, str]] = {}
        self._event_ids: set[tuple[str, str]] = set()

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    def record(self, event: AIWitnessEvent) -> SignedWitnessRecord:
        event = AIWitnessEvent.model_validate(event.model_dump())
        if event.witness_id != self.witness_id:
            raise WitnessValidationError("event witness_id does not match this witness")
        identity = (event.session_id, event.event_id)
        if identity in self._event_ids:
            raise WitnessValidationError("duplicate AI Witness event_id within session")

        head = self._session_heads.get(event.session_id)
        expected_sequence = 0 if head is None else head[0] + 1
        previous_digest = None if head is None else head[1]
        if event.sequence != expected_sequence:
            message = (
                "non-contiguous AI Witness sequence: "
                f"expected {expected_sequence}, got {event.sequence}"
            )
            raise WitnessValidationError(message)

        payload = self._record_payload(event, previous_digest, self.signing_key_id)
        record_digest = canonical_sha256(payload)
        signature = self._private_key.sign(canonicalize(payload)).hex()
        record = SignedWitnessRecord(
            event=event,
            previous_record_digest=previous_digest,
            record_digest=record_digest,
            signing_key_id=self.signing_key_id,
            signature_hex=signature,
        )
        self._session_heads[event.session_id] = (event.sequence, record_digest)
        self._event_ids.add(identity)
        return record

    @staticmethod
    def verify_record(record: SignedWitnessRecord, public_key_hex: str) -> bool:
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError:
            return False
        payload = AIWitnessLedger._record_payload(
            record.event,
            record.previous_record_digest,
            record.signing_key_id,
        )
        if canonical_sha256(payload) != record.record_digest:
            return False
        try:
            public_key.verify(bytes.fromhex(record.signature_hex), canonicalize(payload))
        except (InvalidSignature, ValueError):
            return False
        return True

    @staticmethod
    def verify_chain(records: Iterable[SignedWitnessRecord], public_key_hex: str) -> bool:
        expected_sequence = 0
        previous_digest: str | None = None
        session_id: str | None = None
        seen_event_ids: set[str] = set()
        any_record = False
        for record in records:
            any_record = True
            if not AIWitnessLedger.verify_record(record, public_key_hex):
                return False
            if session_id is None:
                session_id = record.event.session_id
            if record.event.session_id != session_id:
                return False
            if record.event.sequence != expected_sequence:
                return False
            if record.previous_record_digest != previous_digest:
                return False
            if record.event.event_id in seen_event_ids:
                return False
            seen_event_ids.add(record.event.event_id)
            previous_digest = record.record_digest
            expected_sequence += 1
        return any_record

    @staticmethod
    def to_evidence_event(
        record: SignedWitnessRecord,
        *,
        tenant_id: str,
        workspace_id: str,
    ) -> EvidenceEvent:
        event = record.event
        metadata = {
            "ai_witness": {
                "schema_version": record.schema_version,
                "witness_id": event.witness_id,
                "session_id": event.session_id,
                "sequence": event.sequence,
                "kind": event.kind.value,
                "clock_quality": event.clock_quality.value,
                "content_capture": event.content_capture,
                "previous_record_digest": record.previous_record_digest,
                "signing_key_id": record.signing_key_id,
                "signature_hex": record.signature_hex,
                "event": event.model_dump(mode="json"),
            }
        }
        return EvidenceEvent(
            event_id=f"aiw:{event.event_id}",
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            evidence_id=f"aiw:{record.record_digest[:48]}",
            event_type=f"ai_witness.{event.kind.value}",
            subject_ref=event.workload_ref,
            content_hash=record.record_digest,
            content_hash_alg="sha256",
            metadata=metadata,
            created_at_utc=event.observed_at,
            source_system="ets-ai-witness",
            actor_id=None,
            correlation_id=event.session_id,
            external_refs=None,
            redaction_profile="ets.ai-witness.digest-only.v1",
        )

    @staticmethod
    def _record_payload(
        event: AIWitnessEvent,
        previous_digest: str | None,
        signing_key_id: str,
    ) -> dict[str, object]:
        return {
            "schema_version": "ets.ai-witness.record-payload.v1",
            "event": event.model_dump(mode="json"),
            "previous_record_digest": previous_digest,
            "signing_key_id": signing_key_id,
        }
