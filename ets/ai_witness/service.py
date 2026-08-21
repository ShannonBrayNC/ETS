"""AI Witness session chaining, signing, verification, and ETS projection."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Literal

from ets.ai_witness.models import (
    AIWitnessEvent,
    SignedWitnessRecord,
    SigningAlgorithm,
)
from ets.ai_witness.signing import (
    SignerError,
    SoftwareEd25519Signer,
    WitnessSigner,
    verify_signature,
)
from ets.core.api import EvidenceEvent, canonical_sha256, canonicalize

_MAX_EVENT_BYTES = 48 * 1024
RecordSchemaVersion = Literal[
    "ets.ai-witness.record.v1",
    "ets.ai-witness.record.v2",
]


class WitnessValidationError(ValueError):
    """Raised when a witness record violates session or signature invariants."""


class AIWitnessLedger:
    """Reference Witness with per-session chaining and pluggable signing custody."""

    def __init__(
        self,
        *,
        witness_id: str,
        signing_key_id: str | None = None,
        private_key_hex: str | None = None,
        signer: WitnessSigner | None = None,
    ):
        if not witness_id or len(witness_id) > 128:
            raise WitnessValidationError("witness_id must contain 1-128 characters")

        if signer is None:
            if signing_key_id is None or private_key_hex is None:
                raise WitnessValidationError(
                    "software signing requires signing_key_id and private_key_hex"
                )
            try:
                signer = SoftwareEd25519Signer(
                    key_id=signing_key_id,
                    private_key_hex=private_key_hex,
                )
            except SignerError as exc:
                raise WitnessValidationError(str(exc)) from exc
            record_schema: RecordSchemaVersion = "ets.ai-witness.record.v1"
        else:
            if private_key_hex is not None:
                raise WitnessValidationError(
                    "private_key_hex must not be supplied with a signer provider"
                )
            if signing_key_id is not None and signing_key_id != signer.key_id:
                raise WitnessValidationError(
                    "signing_key_id does not match signer provider key_id"
                )
            record_schema = "ets.ai-witness.record.v2"

        if not signer.key_id or len(signer.key_id) > 256:
            raise WitnessValidationError("signing_key_id must contain 1-256 characters")
        if not isinstance(signer.algorithm, SigningAlgorithm):
            raise WitnessValidationError("signer provider returned an unsupported algorithm")

        self.witness_id = witness_id
        self.signing_key_id = signer.key_id
        self._signer = signer
        self._record_schema_version = record_schema
        self._session_heads: dict[str, tuple[int, str]] = {}
        self._event_ids: set[tuple[str, str]] = set()

    @property
    def signing_algorithm(self) -> SigningAlgorithm:
        return self._signer.algorithm

    @property
    def public_key_hex(self) -> str:
        return self._signer.public_key_hex

    @property
    def public_key_fingerprint_sha256(self) -> str:
        try:
            public_key_bytes = bytes.fromhex(self.public_key_hex)
        except ValueError as exc:
            raise WitnessValidationError("signer public key must be hexadecimal") from exc
        return hashlib.sha256(public_key_bytes).hexdigest()

    def record(self, event: AIWitnessEvent) -> SignedWitnessRecord:
        event = AIWitnessEvent.model_validate(event.model_dump())
        if len(canonicalize(event.model_dump(mode="json"))) > _MAX_EVENT_BYTES:
            raise WitnessValidationError("AI Witness event exceeds 48 KiB canonical size")
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

        payload = self._record_payload(
            event,
            previous_digest,
            self.signing_key_id,
            self._record_schema_version,
            self.signing_algorithm,
        )
        canonical_payload = canonicalize(payload)
        record_digest = canonical_sha256(payload)
        signature = self._signer.sign(canonical_payload).hex()
        record = SignedWitnessRecord(
            schema_version=self._record_schema_version,
            event=event,
            previous_record_digest=previous_digest,
            record_digest=record_digest,
            signing_algorithm=self.signing_algorithm,
            signing_key_id=self.signing_key_id,
            signature_hex=signature,
        )
        self._session_heads[event.session_id] = (event.sequence, record_digest)
        self._event_ids.add(identity)
        return record

    @staticmethod
    def verify_record(record: SignedWitnessRecord, public_key_hex: str) -> bool:
        payload = AIWitnessLedger._record_payload(
            record.event,
            record.previous_record_digest,
            record.signing_key_id,
            record.schema_version,
            record.signing_algorithm,
        )
        if canonical_sha256(payload) != record.record_digest:
            return False
        try:
            signature = bytes.fromhex(record.signature_hex)
        except ValueError:
            return False
        return verify_signature(
            record.signing_algorithm,
            public_key_hex,
            canonicalize(payload),
            signature,
        )

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
                "signing_algorithm": record.signing_algorithm.value,
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
        record_schema_version: RecordSchemaVersion,
        signing_algorithm: SigningAlgorithm,
    ) -> dict[str, object]:
        if record_schema_version == "ets.ai-witness.record.v1":
            return {
                "schema_version": "ets.ai-witness.record-payload.v1",
                "event": event.model_dump(mode="json"),
                "previous_record_digest": previous_digest,
                "signing_key_id": signing_key_id,
            }
        return {
            "schema_version": "ets.ai-witness.record-payload.v2",
            "event": event.model_dump(mode="json"),
            "previous_record_digest": previous_digest,
            "signing_algorithm": signing_algorithm.value,
            "signing_key_id": signing_key_id,
        }
