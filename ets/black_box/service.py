"""Rolling capture, trigger sealing, recovery, verification, and ETS projection."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import BaseModel, ConfigDict, Field

from ets.black_box.models import (
    ActiveCaptureState,
    BlackBoxObservation,
    BlackBoxRecorderStatus,
    BlackBoxSegment,
    BlackBoxSegmentManifest,
    BlackBoxTrigger,
    BlackBoxVerification,
    RecorderState,
    SealReason,
    SignedBlackBoxFrame,
    TriggerKind,
)
from ets.black_box.store import BlackBoxStore
from ets.core.api import EvidenceEvent, canonical_sha256, canonicalize

_ZERO_HASH = "0" * 64


class BlackBoxValidationError(ValueError):
    """Raised when recorder input or durable state violates Black Box invariants."""


class BlackBoxProductionReadinessError(RuntimeError):
    """Raised when a backend cannot support the requested production claim."""


class BlackBoxPolicy(BaseModel):
    """Bounded rolling-capture and production-readiness controls."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    pre_trigger_frames: int = Field(default=256, ge=1, le=1_000_000)
    post_trigger_frames: int = Field(default=64, ge=0, le=1_000_000)
    max_observation_bytes: int = Field(default=32 * 1024, ge=1024, le=1024 * 1024)
    require_production_backend: bool = False


class BlackBoxRecorder:
    """Reference ETS Black Box event recorder with signed, sealed incident windows."""

    def __init__(
        self,
        store: BlackBoxStore,
        *,
        device_id: str,
        signing_key_id: str,
        private_key_hex: str,
        boot_id: str,
        boot_counter: int,
        policy: BlackBoxPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not device_id.startswith("ets-black-box:") or len(device_id) > 160:
            raise BlackBoxValidationError("device_id must use the ets-black-box: namespace")
        if not signing_key_id or len(signing_key_id) > 256:
            raise BlackBoxValidationError("signing_key_id must contain 1-256 characters")
        if not boot_id or len(boot_id) > 128:
            raise BlackBoxValidationError("boot_id must contain 1-128 characters")
        if boot_counter < 1:
            raise BlackBoxValidationError("boot_counter must be at least one")
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except ValueError as exc:
            raise BlackBoxValidationError("private key must be a 32-byte Ed25519 key") from exc

        self._store = store
        self._policy = policy or BlackBoxPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self.device_id = device_id
        self.signing_key_id = signing_key_id

        if self._policy.require_production_backend and not store.capabilities.production_ready():
            raise BlackBoxProductionReadinessError(
                f"Black Box backend {store.provider_name!r} does not satisfy the production floor"
            )

        state = store.load_state()
        if state is None:
            state = RecorderState(
                device_id=device_id,
                signing_key_id=signing_key_id,
                boot_id=boot_id,
                boot_counter=boot_counter,
            )
            store.initialize_state(state)
        else:
            self._validate_persisted_identity(state)
            if boot_counter < state.boot_counter:
                raise BlackBoxValidationError("boot counter rollback detected")
            if boot_counter == state.boot_counter and boot_id != state.boot_id:
                raise BlackBoxValidationError("boot_id changed without advancing boot_counter")
            if boot_counter > state.boot_counter:
                state = state.model_copy(
                    update={
                        "boot_id": boot_id,
                        "boot_counter": boot_counter,
                        "last_monotonic_ns": None,
                    }
                )
                store.update_state(state)

        self._state = state
        self._verify_live_state()
        if self._state.active_capture is not None and (
            self._state.active_capture.remaining_post_frames == 0
        ):
            self._seal_active(SealReason.RECOVERY)

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def public_key_fingerprint_sha256(self) -> str:
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()

    @property
    def state(self) -> RecorderState:
        return self._state

    def record(self, observation: BlackBoxObservation) -> SignedBlackBoxFrame:
        """Atomically append one signed frame and advance durable recorder state."""

        observation = BlackBoxObservation.model_validate(observation.model_dump())
        encoded = canonicalize(observation.model_dump(mode="json"))
        if len(encoded) > self._policy.max_observation_bytes:
            raise BlackBoxValidationError("Black Box observation exceeds configured size limit")
        if observation.device_id != self.device_id:
            raise BlackBoxValidationError("observation device_id does not match this recorder")
        if observation.boot_id != self._state.boot_id:
            raise BlackBoxValidationError("observation boot_id does not match the active boot")
        if (
            self._state.last_monotonic_ns is not None
            and observation.monotonic_ns <= self._state.last_monotonic_ns
        ):
            raise BlackBoxValidationError("monotonic_ns must strictly increase within a boot")

        sequence = self._state.last_sequence + 1
        payload = self._frame_payload(
            sequence=sequence,
            boot_counter=self._state.boot_counter,
            observation=observation,
            previous_frame_hash=self._state.head_hash,
            signing_key_id=self.signing_key_id,
        )
        frame_hash = canonical_sha256(payload)
        signature_hex = self._private_key.sign(canonicalize(payload)).hex()
        frame = SignedBlackBoxFrame(
            sequence=sequence,
            boot_counter=self._state.boot_counter,
            observation=observation,
            previous_frame_hash=self._state.head_hash,
            frame_hash=frame_hash,
            signing_key_id=self.signing_key_id,
            signature_hex=signature_hex,
        )

        active = self._state.active_capture
        if active is not None and active.remaining_post_frames > 0:
            active = active.model_copy(
                update={"remaining_post_frames": active.remaining_post_frames - 1}
            )
        next_state = self._state.model_copy(
            update={
                "last_sequence": sequence,
                "head_hash": frame_hash,
                "last_monotonic_ns": observation.monotonic_ns,
                "active_capture": active,
            }
        )
        self._store.commit_frame(frame, next_state)
        self._state = next_state

        if active is not None and active.remaining_post_frames == 0:
            self._seal_active(SealReason.POST_WINDOW_COMPLETE)
        elif active is None:
            self._prune_rolling_window()
        return frame

    def trigger(
        self,
        *,
        trigger_id: str,
        kind: TriggerKind,
        reason: str,
        actor_ref: str | None = None,
        triggered_at_utc: datetime | None = None,
    ) -> BlackBoxSegment | None:
        """Freeze the rolling pre-event window and begin bounded post-trigger capture."""

        if self._state.active_capture is not None:
            raise BlackBoxValidationError("an incident capture is already active")
        live = self._store.list_live_frames()
        if not live:
            raise BlackBoxValidationError("cannot trigger before at least one frame is recorded")
        triggered_at = self._normalize_utc(triggered_at_utc or self._now(), "triggered_at_utc")
        first_sequence = max(
            live[0].sequence,
            self._state.last_sequence - self._policy.pre_trigger_frames + 1,
        )
        trigger = BlackBoxTrigger(
            trigger_id=trigger_id,
            kind=kind,
            reason=reason,
            triggered_at_utc=triggered_at,
            trigger_sequence=self._state.last_sequence,
            actor_ref=actor_ref,
        )
        active = ActiveCaptureState(
            trigger=trigger,
            first_sequence=first_sequence,
            remaining_post_frames=self._policy.post_trigger_frames,
        )
        self._state = self._state.model_copy(update={"active_capture": active})
        self._store.update_state(self._state)
        if active.remaining_post_frames == 0:
            return self._seal_active(SealReason.POST_WINDOW_COMPLETE)
        return None

    def force_seal(self, reason: SealReason) -> BlackBoxSegment:
        """Seal a partial incident window, such as on power-loss-imminent notification."""

        if reason not in {SealReason.POWER_LOSS_IMMINENT, SealReason.OPERATOR, SealReason.RECOVERY}:
            raise BlackBoxValidationError("force_seal requires a forced-seal reason")
        if self._state.active_capture is None:
            raise BlackBoxValidationError("no incident capture is active")
        return self._seal_active(reason)

    def get_segment(self, segment_id: str) -> BlackBoxSegment:
        return self._store.get_segment(segment_id)

    def list_segments(self) -> list[BlackBoxSegment]:
        return self._store.list_segments()

    def status(self) -> BlackBoxRecorderStatus:
        active = self._state.active_capture
        return BlackBoxRecorderStatus(
            device_id=self.device_id,
            boot_id=self._state.boot_id,
            boot_counter=self._state.boot_counter,
            last_sequence=self._state.last_sequence,
            head_hash=self._state.head_hash,
            live_frame_count=len(self._store.list_live_frames()),
            sealed_segment_count=len(self._store.list_segments()),
            capture_active=active is not None,
            remaining_post_frames=None if active is None else active.remaining_post_frames,
        )

    @staticmethod
    def verify_frame(frame: SignedBlackBoxFrame, public_key_hex: str) -> bool:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        except ValueError:
            return False
        payload = BlackBoxRecorder._frame_payload(
            sequence=frame.sequence,
            boot_counter=frame.boot_counter,
            observation=frame.observation,
            previous_frame_hash=frame.previous_frame_hash,
            signing_key_id=frame.signing_key_id,
        )
        if canonical_sha256(payload) != frame.frame_hash:
            return False
        try:
            public_key.verify(bytes.fromhex(frame.signature_hex), canonicalize(payload))
        except (InvalidSignature, ValueError):
            return False
        return True

    @staticmethod
    def verify_segment(segment: BlackBoxSegment, public_key_hex: str) -> BlackBoxVerification:
        frames = segment.frames
        manifest = segment.manifest
        if not frames:
            return BlackBoxVerification(
                valid=False,
                reason="segment contains no frames",
                frame_count=0,
            )
        previous = manifest.predecessor_frame_hash
        expected_sequence = manifest.first_sequence
        for frame in frames:
            if frame.sequence != expected_sequence:
                return BlackBoxVerification(
                    valid=False,
                    reason=f"sequence gap at frame {expected_sequence}",
                    frame_count=len(frames),
                    segment_hash=manifest.segment_hash,
                )
            if frame.previous_frame_hash != previous:
                return BlackBoxVerification(
                    valid=False,
                    reason=f"hash-chain mismatch at frame {frame.sequence}",
                    frame_count=len(frames),
                    segment_hash=manifest.segment_hash,
                )
            if not BlackBoxRecorder.verify_frame(frame, public_key_hex):
                return BlackBoxVerification(
                    valid=False,
                    reason=f"invalid frame signature or digest at frame {frame.sequence}",
                    frame_count=len(frames),
                    segment_hash=manifest.segment_hash,
                )
            previous = frame.frame_hash
            expected_sequence += 1

        if previous != manifest.chain_head_hash:
            return BlackBoxVerification(
                valid=False,
                reason="manifest chain head does not match final frame",
                frame_count=len(frames),
                segment_hash=manifest.segment_hash,
            )
        payload = BlackBoxRecorder._segment_payload(
            device_id=manifest.device_id,
            trigger=manifest.trigger,
            first_sequence=manifest.first_sequence,
            last_sequence=manifest.last_sequence,
            first_observed_at_utc=manifest.first_observed_at_utc,
            last_observed_at_utc=manifest.last_observed_at_utc,
            sealed_at_utc=manifest.sealed_at_utc,
            seal_reason=manifest.seal_reason,
            predecessor_frame_hash=manifest.predecessor_frame_hash,
            chain_head_hash=manifest.chain_head_hash,
            frame_hashes=tuple(frame.frame_hash for frame in frames),
            signing_key_id=manifest.signing_key_id,
        )
        expected_hash = canonical_sha256(payload)
        if (
            manifest.segment_hash != expected_hash
            or manifest.segment_id != f"bbxseg:{expected_hash}"
        ):
            return BlackBoxVerification(
                valid=False,
                reason="segment manifest digest or identifier does not match frames",
                frame_count=len(frames),
                segment_hash=manifest.segment_hash,
            )
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            public_key.verify(bytes.fromhex(manifest.signature_hex), canonicalize(payload))
        except (InvalidSignature, ValueError):
            return BlackBoxVerification(
                valid=False,
                reason="segment manifest signature is invalid",
                frame_count=len(frames),
                segment_hash=manifest.segment_hash,
            )
        return BlackBoxVerification(
            valid=True,
            reason="sealed Black Box segment, frame chain, and signatures are valid",
            frame_count=len(frames),
            segment_hash=manifest.segment_hash,
        )

    @staticmethod
    def to_evidence_event(
        segment: BlackBoxSegment,
        *,
        tenant_id: str,
        workspace_id: str,
    ) -> EvidenceEvent:
        """Project a sealed manifest into Core without copying captured frame attributes."""

        manifest = segment.manifest
        metadata = {
            "black_box": {
                "schema_version": manifest.schema_version,
                "segment_id": manifest.segment_id,
                "device_id": manifest.device_id,
                "trigger": {
                    "trigger_id": manifest.trigger.trigger_id,
                    "kind": manifest.trigger.kind.value,
                    "triggered_at_utc": manifest.trigger.triggered_at_utc.isoformat(),
                    "trigger_sequence": manifest.trigger.trigger_sequence,
                },
                "first_sequence": manifest.first_sequence,
                "last_sequence": manifest.last_sequence,
                "frame_count": manifest.frame_count,
                "first_observed_at_utc": manifest.first_observed_at_utc.isoformat(),
                "last_observed_at_utc": manifest.last_observed_at_utc.isoformat(),
                "sealed_at_utc": manifest.sealed_at_utc.isoformat(),
                "seal_reason": manifest.seal_reason.value,
                "predecessor_frame_hash": manifest.predecessor_frame_hash,
                "chain_head_hash": manifest.chain_head_hash,
                "signing_key_id": manifest.signing_key_id,
                "signature_hex": manifest.signature_hex,
            }
        }
        return EvidenceEvent(
            event_id=f"bbx:{manifest.segment_hash[:48]}",
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            evidence_id=f"bbx:{manifest.segment_hash[:48]}",
            event_type="black_box.segment.sealed",
            subject_ref=manifest.device_id,
            content_hash=manifest.segment_hash,
            content_hash_alg="sha256",
            metadata=metadata,
            created_at_utc=manifest.sealed_at_utc,
            source_system="ets-black-box",
            actor_id=None,
            correlation_id=manifest.trigger.trigger_id,
            external_refs=None,
            redaction_profile="none",
        )

    def _seal_active(self, reason: SealReason) -> BlackBoxSegment:
        active = self._state.active_capture
        if active is None:
            raise BlackBoxValidationError("no incident capture is active")
        frames = tuple(
            frame
            for frame in self._store.list_live_frames()
            if active.first_sequence <= frame.sequence <= self._state.last_sequence
        )
        if not frames or frames[0].sequence != active.first_sequence:
            raise BlackBoxValidationError("frozen pre-trigger frames are missing")
        expected_sequences = tuple(range(active.first_sequence, self._state.last_sequence + 1))
        if tuple(frame.sequence for frame in frames) != expected_sequences:
            raise BlackBoxValidationError("incident capture contains a sequence gap")
        sealed_at = self._now()
        payload = self._segment_payload(
            device_id=self.device_id,
            trigger=active.trigger,
            first_sequence=frames[0].sequence,
            last_sequence=frames[-1].sequence,
            first_observed_at_utc=frames[0].observation.observed_at_utc,
            last_observed_at_utc=frames[-1].observation.observed_at_utc,
            sealed_at_utc=sealed_at,
            seal_reason=reason,
            predecessor_frame_hash=frames[0].previous_frame_hash,
            chain_head_hash=frames[-1].frame_hash,
            frame_hashes=tuple(frame.frame_hash for frame in frames),
            signing_key_id=self.signing_key_id,
        )
        segment_hash = canonical_sha256(payload)
        manifest = BlackBoxSegmentManifest(
            segment_id=f"bbxseg:{segment_hash}",
            device_id=self.device_id,
            trigger=active.trigger,
            first_sequence=frames[0].sequence,
            last_sequence=frames[-1].sequence,
            frame_count=len(frames),
            first_observed_at_utc=frames[0].observation.observed_at_utc,
            last_observed_at_utc=frames[-1].observation.observed_at_utc,
            sealed_at_utc=sealed_at,
            seal_reason=reason,
            predecessor_frame_hash=frames[0].previous_frame_hash,
            chain_head_hash=frames[-1].frame_hash,
            segment_hash=segment_hash,
            signing_key_id=self.signing_key_id,
            signature_hex=self._private_key.sign(canonicalize(payload)).hex(),
        )
        segment = BlackBoxSegment(manifest=manifest, frames=frames)
        next_state = self._state.model_copy(update={"active_capture": None})
        self._store.seal_segment(segment, next_state)
        self._state = next_state
        self._prune_rolling_window()
        return segment

    def _prune_rolling_window(self) -> None:
        minimum = max(1, self._state.last_sequence - self._policy.pre_trigger_frames + 1)
        self._store.prune_live_before(minimum)

    def _validate_persisted_identity(self, state: RecorderState) -> None:
        if state.device_id != self.device_id:
            raise BlackBoxValidationError("persisted recorder belongs to another device")
        if state.signing_key_id != self.signing_key_id:
            raise BlackBoxValidationError("persisted recorder signing key identifier changed")

    def _verify_live_state(self) -> None:
        frames = self._store.list_live_frames()
        if not frames:
            if self._state.last_sequence != 0:
                raise BlackBoxValidationError("persisted state has no live recovery frames")
            if self._state.head_hash != _ZERO_HASH:
                raise BlackBoxValidationError("empty recorder state has a nonzero chain head")
            return
        previous = frames[0].previous_frame_hash
        expected_sequence = frames[0].sequence
        for frame in frames:
            if frame.sequence != expected_sequence or frame.previous_frame_hash != previous:
                raise BlackBoxValidationError("persisted live frame chain is inconsistent")
            if frame.signing_key_id != self.signing_key_id:
                raise BlackBoxValidationError("persisted frame signing key identifier changed")
            if not self.verify_frame(frame, self.public_key_hex):
                raise BlackBoxValidationError("persisted live frame signature is invalid")
            previous = frame.frame_hash
            expected_sequence += 1
        if frames[-1].sequence != self._state.last_sequence:
            raise BlackBoxValidationError("persisted state sequence does not match live frame head")
        if frames[-1].frame_hash != self._state.head_hash:
            raise BlackBoxValidationError("persisted state hash does not match live frame head")
        active = self._state.active_capture
        if active is not None and frames[0].sequence > active.first_sequence:
            raise BlackBoxValidationError("active capture lost its frozen pre-trigger window")

    @staticmethod
    def _frame_payload(
        *,
        sequence: int,
        boot_counter: int,
        observation: BlackBoxObservation,
        previous_frame_hash: str,
        signing_key_id: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": "ets.black-box.frame-payload.v1",
            "sequence": sequence,
            "boot_counter": boot_counter,
            "observation": observation.model_dump(mode="json"),
            "previous_frame_hash": previous_frame_hash,
            "signing_key_id": signing_key_id,
        }

    @staticmethod
    def _segment_payload(
        *,
        device_id: str,
        trigger: BlackBoxTrigger,
        first_sequence: int,
        last_sequence: int,
        first_observed_at_utc: datetime,
        last_observed_at_utc: datetime,
        sealed_at_utc: datetime,
        seal_reason: SealReason,
        predecessor_frame_hash: str,
        chain_head_hash: str,
        frame_hashes: tuple[str, ...],
        signing_key_id: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": "ets.black-box.segment-payload.v1",
            "device_id": device_id,
            "trigger": trigger.model_dump(mode="json"),
            "first_sequence": first_sequence,
            "last_sequence": last_sequence,
            "frame_count": len(frame_hashes),
            "first_observed_at_utc": first_observed_at_utc.isoformat(),
            "last_observed_at_utc": last_observed_at_utc.isoformat(),
            "sealed_at_utc": sealed_at_utc.isoformat(),
            "seal_reason": seal_reason.value,
            "predecessor_frame_hash": predecessor_frame_hash,
            "chain_head_hash": chain_head_hash,
            "frame_hashes": list(frame_hashes),
            "signing_key_id": signing_key_id,
        }

    def _now(self) -> datetime:
        return self._normalize_utc(self._clock(), "clock")

    @staticmethod
    def _normalize_utc(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BlackBoxValidationError(f"{field} must be timezone-aware")
        return value.astimezone(UTC)
