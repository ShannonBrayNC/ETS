"""Retention, integrity, and administrative controls for ETS Vault."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ets.core import canonical_sha256
from ets.vault.models import (
    RetentionMode,
    VaultAuthorization,
    VaultIntegrityResult,
    VaultJournalEntry,
    VaultJournalVerification,
    VaultReceipt,
    VaultRecord,
    VaultRetention,
)
from ets.vault.store import VaultBackend, VaultCatalog, VaultObjectNotFound

_ZERO_HASH = "0" * 64


class VaultPolicyError(ValueError):
    """Raised when a Vault operation would violate retention or safety policy."""


class VaultProductionReadinessError(RuntimeError):
    """Raised when a backend does not satisfy the Vault production boundary."""


class VaultPolicy(BaseModel):
    """Fail-closed controls applied by the Vault service."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    require_production_backend: bool = False
    max_object_bytes: int = Field(default=64 * 1024 * 1024, ge=1)
    require_dual_control_for_hold_release: bool = True
    require_dual_control_for_purge: bool = True


class VaultService:
    """Coordinate immutable storage, retention policy, and tamper-evident audit."""

    def __init__(
        self,
        backend: VaultBackend,
        catalog: VaultCatalog,
        *,
        policy: VaultPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._backend = backend
        self._catalog = catalog
        self._policy = policy or VaultPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))

        if (
            self._policy.require_production_backend
            and not self._backend.capabilities.production_ready()
        ):
            raise VaultProductionReadinessError(
                f"Vault backend {self._backend.provider_name!r} does not satisfy "
                "the production capability floor"
            )

    def preserve(
        self,
        payload: bytes,
        *,
        tenant_id: str,
        workspace_id: str,
        media_type: str,
        retain_until_utc: datetime,
        actor_id: str,
        retention_mode: RetentionMode = "compliance",
        source_event_id: str | None = None,
        legal_holds: tuple[str, ...] = (),
        expected_sha256: str | None = None,
    ) -> VaultReceipt:
        """Preserve bytes once and bind them to immutable retention state."""

        now = self._now()
        retain_until = self._normalize_utc(retain_until_utc, "retain_until_utc")
        if retain_until <= now:
            raise VaultPolicyError("retain_until_utc must be in the future")
        if len(payload) > self._policy.max_object_bytes:
            raise VaultPolicyError("payload exceeds configured Vault object limit")

        content_hash = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None:
            self._require_sha256(expected_sha256)
            if content_hash != expected_sha256:
                raise VaultPolicyError("payload hash does not match expected_sha256")

        object_id = self._new_object_id(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            content_hash=content_hash,
        )
        retention = VaultRetention(
            mode=retention_mode,
            retain_until_utc=retain_until,
            legal_holds=legal_holds,
        )
        record = VaultRecord(
            object_id=object_id,
            content_hash=content_hash,
            byte_size=len(payload),
            media_type=media_type,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            source_event_id=source_event_id,
            received_at_utc=now,
            retention=retention,
        )

        self._backend.put_once(object_id, payload, retention)
        self._catalog.create_record(record)
        head = self._append_journal(
            operation="preserve",
            record=record,
            actor_id=actor_id,
            reason="object preserved under Vault retention policy",
            occurred_at_utc=now,
        )
        return VaultReceipt(record=record, journal_head_hash=head)

    def get_receipt(self, object_id: str) -> VaultReceipt:
        """Return current Vault metadata plus the global administrative journal head."""

        record = self._catalog.get_record(object_id)
        return VaultReceipt(record=record, journal_head_hash=self._journal_head_hash())

    def read(self, object_id: str) -> bytes:
        """Read preserved bytes unless the logical record has been purged."""

        record = self._catalog.get_record(object_id)
        if record.purged_at_utc is not None:
            raise VaultObjectNotFound(object_id)
        return self._backend.get(object_id)

    def verify_integrity(self, object_id: str) -> VaultIntegrityResult:
        """Re-read content and verify size and SHA-256 against the Vault record."""

        record = self._catalog.get_record(object_id)
        if record.purged_at_utc is not None:
            return VaultIntegrityResult(
                valid=False,
                object_id=object_id,
                reason="object has been purged after retention expiry",
                expected_hash=record.content_hash,
                actual_hash=None,
                expected_byte_size=record.byte_size,
                actual_byte_size=None,
            )

        try:
            payload = self._backend.get(object_id)
        except VaultObjectNotFound:
            return VaultIntegrityResult(
                valid=False,
                object_id=object_id,
                reason="catalog record exists but preserved bytes are missing",
                expected_hash=record.content_hash,
                actual_hash=None,
                expected_byte_size=record.byte_size,
                actual_byte_size=None,
            )

        actual_hash = hashlib.sha256(payload).hexdigest()
        valid = actual_hash == record.content_hash and len(payload) == record.byte_size
        return VaultIntegrityResult(
            valid=valid,
            object_id=object_id,
            reason="content hash and size match Vault record" if valid else
            "preserved content does not match Vault record",
            expected_hash=record.content_hash,
            actual_hash=actual_hash,
            expected_byte_size=record.byte_size,
            actual_byte_size=len(payload),
        )

    def extend_retention(
        self,
        object_id: str,
        *,
        retain_until_utc: datetime,
        actor_id: str,
        retention_mode: RetentionMode | None = None,
        reason: str = "retention extended",
    ) -> VaultReceipt:
        """Extend retention or upgrade governance mode to compliance; never weaken it."""

        current = self._active_record(object_id)
        retain_until = self._normalize_utc(retain_until_utc, "retain_until_utc")
        target_mode = retention_mode or current.retention.mode
        if retain_until < current.retention.retain_until_utc:
            raise VaultPolicyError("Vault retention may never be shortened")
        if current.retention.mode == "compliance" and target_mode != "compliance":
            raise VaultPolicyError("compliance retention may never be downgraded")
        if (
            retain_until == current.retention.retain_until_utc
            and target_mode == current.retention.mode
        ):
            raise VaultPolicyError("retention update must extend time or strengthen mode")

        retention = VaultRetention(
            mode=target_mode,
            retain_until_utc=retain_until,
            legal_holds=current.retention.legal_holds,
        )
        updated = self._next_record(current, retention=retention)
        self._backend.extend_retention(object_id, retention)
        self._catalog.update_record(updated)
        head = self._append_journal(
            operation="retention_extended",
            record=updated,
            actor_id=actor_id,
            reason=reason,
        )
        return VaultReceipt(record=updated, journal_head_hash=head)

    def apply_legal_hold(
        self,
        object_id: str,
        *,
        hold_id: str,
        actor_id: str,
        reason: str,
    ) -> VaultReceipt:
        """Apply a named legal/event hold without altering time-based retention."""

        current = self._active_record(object_id)
        normalized_hold = hold_id.strip()
        if not normalized_hold:
            raise VaultPolicyError("hold_id must not be blank")
        if normalized_hold in current.retention.legal_holds:
            return self.get_receipt(object_id)

        retention = VaultRetention(
            mode=current.retention.mode,
            retain_until_utc=current.retention.retain_until_utc,
            legal_holds=(*current.retention.legal_holds, normalized_hold),
        )
        updated = self._next_record(current, retention=retention)
        self._backend.apply_legal_hold(object_id, retention)
        self._catalog.update_record(updated)
        head = self._append_journal(
            operation="legal_hold_applied",
            record=updated,
            actor_id=actor_id,
            reason=reason,
        )
        return VaultReceipt(record=updated, journal_head_hash=head)

    def release_legal_hold(
        self,
        object_id: str,
        *,
        hold_id: str,
        authorization: VaultAuthorization,
    ) -> VaultReceipt:
        """Release a named hold under explicit dual-control authorization."""

        current = self._active_record(object_id)
        normalized_hold = hold_id.strip()
        if normalized_hold not in current.retention.legal_holds:
            raise VaultPolicyError("requested legal hold is not active")
        if self._policy.require_dual_control_for_hold_release:
            self._require_dual_control(authorization)

        remaining = tuple(
            hold for hold in current.retention.legal_holds if hold != normalized_hold
        )
        retention = VaultRetention(
            mode=current.retention.mode,
            retain_until_utc=current.retention.retain_until_utc,
            legal_holds=remaining,
        )
        updated = self._next_record(current, retention=retention)
        self._backend.release_legal_hold(object_id, retention)
        self._catalog.update_record(updated)
        head = self._append_journal(
            operation="legal_hold_released",
            record=updated,
            actor_id=authorization.primary_actor_id,
            secondary_actor_id=authorization.secondary_actor_id,
            reason=authorization.reason,
        )
        return VaultReceipt(record=updated, journal_head_hash=head)

    def purge(
        self,
        object_id: str,
        *,
        authorization: VaultAuthorization,
    ) -> VaultReceipt:
        """Purge content only after retention expiry, no holds, and dual control."""

        current = self._active_record(object_id)
        now = self._now()
        if now < current.retention.retain_until_utc:
            raise VaultPolicyError("object is still inside its retention period")
        if current.retention.legal_holds:
            raise VaultPolicyError("object cannot be purged while a legal hold is active")
        if self._policy.require_dual_control_for_purge:
            self._require_dual_control(authorization)

        self._backend.delete(object_id)
        updated = self._next_record(current, purged_at_utc=now)
        self._catalog.update_record(updated)
        head = self._append_journal(
            operation="purged",
            record=updated,
            actor_id=authorization.primary_actor_id,
            secondary_actor_id=authorization.secondary_actor_id,
            reason=authorization.reason,
            occurred_at_utc=now,
        )
        return VaultReceipt(record=updated, journal_head_hash=head)

    def verify_journal(self) -> VaultJournalVerification:
        """Verify sequence, previous-hash binding, and every journal entry hash."""

        entries = self._catalog.list_journal()
        previous = _ZERO_HASH
        for expected_sequence, entry in enumerate(entries, start=1):
            if entry.sequence != expected_sequence:
                return VaultJournalVerification(
                    valid=False,
                    reason=f"journal sequence mismatch at entry {expected_sequence}",
                    entry_count=len(entries),
                    head_hash=previous,
                )
            if entry.previous_entry_hash != previous:
                return VaultJournalVerification(
                    valid=False,
                    reason=f"journal previous hash mismatch at entry {expected_sequence}",
                    entry_count=len(entries),
                    head_hash=previous,
                )
            expected_hash = canonical_sha256(self._journal_payload(entry))
            if entry.entry_hash != expected_hash:
                return VaultJournalVerification(
                    valid=False,
                    reason=f"journal entry hash mismatch at entry {expected_sequence}",
                    entry_count=len(entries),
                    head_hash=previous,
                )
            previous = entry.entry_hash

        return VaultJournalVerification(
            valid=True,
            reason="Vault administration journal hash chain is valid",
            entry_count=len(entries),
            head_hash=previous,
        )

    def _active_record(self, object_id: str) -> VaultRecord:
        record = self._catalog.get_record(object_id)
        if record.purged_at_utc is not None:
            raise VaultPolicyError("purged Vault records cannot be modified")
        return record

    @staticmethod
    def _next_record(
        current: VaultRecord,
        *,
        retention: VaultRetention | None = None,
        purged_at_utc: datetime | None = None,
    ) -> VaultRecord:
        return VaultRecord(
            object_id=current.object_id,
            content_hash=current.content_hash,
            byte_size=current.byte_size,
            media_type=current.media_type,
            tenant_id=current.tenant_id,
            workspace_id=current.workspace_id,
            source_event_id=current.source_event_id,
            received_at_utc=current.received_at_utc,
            retention=retention or current.retention,
            generation=current.generation + 1,
            purged_at_utc=purged_at_utc,
        )

    def _append_journal(
        self,
        *,
        operation: Literal[
            "preserve",
            "retention_extended",
            "legal_hold_applied",
            "legal_hold_released",
            "purged",
        ],
        record: VaultRecord,
        actor_id: str,
        reason: str,
        secondary_actor_id: str | None = None,
        occurred_at_utc: datetime | None = None,
    ) -> str:
        entries = self._catalog.list_journal()
        previous = entries[-1].entry_hash if entries else _ZERO_HASH
        occurred_at = occurred_at_utc or self._now()
        payload: dict[str, Any] = {
            "schema_version": "ets.vault_journal.v1",
            "sequence": len(entries) + 1,
            "operation": operation,
            "object_id": record.object_id,
            "record_generation": record.generation,
            "actor_id": actor_id,
            "secondary_actor_id": secondary_actor_id,
            "reason": reason,
            "occurred_at_utc": self._format_utc(occurred_at),
            "previous_entry_hash": previous,
        }
        entry_hash = canonical_sha256(payload)
        entry = VaultJournalEntry(
            sequence=len(entries) + 1,
            operation=operation,
            object_id=record.object_id,
            record_generation=record.generation,
            actor_id=actor_id,
            secondary_actor_id=secondary_actor_id,
            reason=reason,
            occurred_at_utc=occurred_at,
            previous_entry_hash=previous,
            entry_hash=entry_hash,
        )
        self._catalog.append_journal(entry)
        return entry_hash

    @classmethod
    def _journal_payload(cls, entry: VaultJournalEntry) -> dict[str, Any]:
        return {
            "schema_version": entry.schema_version,
            "sequence": entry.sequence,
            "operation": entry.operation,
            "object_id": entry.object_id,
            "record_generation": entry.record_generation,
            "actor_id": entry.actor_id,
            "secondary_actor_id": entry.secondary_actor_id,
            "reason": entry.reason,
            "occurred_at_utc": cls._format_utc(entry.occurred_at_utc),
            "previous_entry_hash": entry.previous_entry_hash,
        }

    def _journal_head_hash(self) -> str:
        entries = self._catalog.list_journal()
        return entries[-1].entry_hash if entries else _ZERO_HASH

    def _new_object_id(self, *, tenant_id: str, workspace_id: str, content_hash: str) -> str:
        nonce = self._nonce_factory()
        if not nonce:
            raise VaultPolicyError("Vault nonce factory returned an empty value")
        digest = canonical_sha256(
            {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "content_hash": content_hash,
                "nonce": nonce,
            }
        )
        return f"vault:{digest}"

    def _now(self) -> datetime:
        return self._normalize_utc(self._clock(), "Vault clock")

    @staticmethod
    def _normalize_utc(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise VaultPolicyError(f"{field_name} must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def _format_utc(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _require_sha256(value: str) -> None:
        if len(value) != 64:
            raise VaultPolicyError("expected_sha256 must be a 64-character SHA-256 digest")
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise VaultPolicyError("expected_sha256 must be hexadecimal") from exc

    @staticmethod
    def _require_dual_control(authorization: VaultAuthorization) -> None:
        if authorization.primary_actor_id == authorization.secondary_actor_id:
            raise VaultPolicyError("dual-control actions require two distinct actors")
