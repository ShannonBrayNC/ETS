"""Durable trust-mutation journal composition for ETS Fleet C3A."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import ValidationError

from ets.fleet.models import ScopeBinding, normalize_time
from ets.fleet.portal import FleetPrincipal
from ets.fleet.portal_admin import (
    FleetAdminAction,
    FleetAdminIdempotencyConflict,
    FleetAdministrativeEvidence,
    FleetMutationResult,
    FleetPortalAdminService,
    FleetSecuritySession,
    InMemoryFleetAdministrativeEvidenceSink,
    _request_fingerprint,
    _sha256,
)
from ets.fleet.service import DeviceEnrollmentService
from ets.fleet.store import EnrollmentStore


class FleetAdminMutationPending(RuntimeError):
    """A prior mutation may have applied and requires reconciliation before retry."""


class FleetAdminDurabilityError(RuntimeError):
    """Durable Fleet mutation state is missing, corrupt, or inconsistent."""


class FleetAdminMutationJournal(Protocol):
    """Provider-neutral reservation/commit contract for privileged Fleet mutations."""

    def reserve(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        now: datetime,
    ) -> FleetMutationResult | None: ...

    def commit(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        result: FleetMutationResult,
        evidence: FleetAdministrativeEvidence,
        now: datetime,
    ) -> None: ...

    def list_records(self) -> list[FleetAdministrativeEvidence]: ...


class DurableFleetPortalAdminService(FleetPortalAdminService):
    """C2 authorization/lifecycle semantics with durable replay/evidence retention."""

    def __init__(
        self,
        *,
        enrollment_service: DeviceEnrollmentService,
        enrollment_store: EnrollmentStore,
        journal: FleetAdminMutationJournal,
    ) -> None:
        super().__init__(
            enrollment_service=enrollment_service,
            enrollment_store=enrollment_store,
            evidence_sink=InMemoryFleetAdministrativeEvidenceSink(),
        )
        self._journal = journal

    def mutate(
        self,
        *,
        principal: FleetPrincipal,
        security_session: FleetSecuritySession,
        action: FleetAdminAction,
        device_id: str,
        idempotency_key: str,
        csrf_token: str,
        confirmation: str | None = None,
        replacement_enrollment_id: str | None = None,
        overlap_expires_at_utc: datetime | None = None,
        now: datetime | None = None,
    ) -> FleetMutationResult:
        current_time = normalize_time(now or datetime.now(UTC))
        key = self._validate_idempotency_key(idempotency_key)
        self._require_csrf(security_session, csrf_token)
        self._authorize_role(principal, security_session, action, now=current_time)
        current = self._current_authorized_record(principal, device_id)
        self._require_confirmation(action, device_id, confirmation)
        self._validate_action_inputs(
            action=action,
            replacement_enrollment_id=replacement_enrollment_id,
            overlap_expires_at_utc=overlap_expires_at_utc,
        )

        request_fingerprint = _request_fingerprint(
            action=action,
            device_id=device_id,
            confirmation=confirmation,
            replacement_enrollment_id=replacement_enrollment_id,
            overlap_expires_at_utc=overlap_expires_at_utc,
        )
        idempotency_hash = _sha256(key)
        retained = self._journal.reserve(
            actor_subject=principal.subject,
            idempotency_key_sha256=idempotency_hash,
            request_fingerprint_sha256=request_fingerprint,
            now=current_time,
        )
        if retained is not None:
            return retained.model_copy(update={"idempotent_replay": True})

        updated = self._apply(
            action=action,
            current=current,
            replacement_enrollment_id=replacement_enrollment_id,
            overlap_expires_at_utc=overlap_expires_at_utc,
            now=current_time,
        )
        evidence = self._evidence(
            principal=principal,
            action=action,
            updated=updated,
            request_fingerprint=request_fingerprint,
            idempotency_key=key,
            now=current_time,
        )
        result = FleetMutationResult(
            action=action,
            device_id=updated.device_id,
            enrollment_id=updated.enrollment_id,
            resulting_state=updated.registration_state,
            administrative_evidence_id=evidence.evidence_id,
        )
        self._journal.commit(
            actor_subject=principal.subject,
            idempotency_key_sha256=idempotency_hash,
            request_fingerprint_sha256=request_fingerprint,
            result=result,
            evidence=evidence,
            now=current_time,
        )
        return result

    def audit_export(
        self,
        principal: FleetPrincipal,
        *,
        limit: int = 200,
    ) -> tuple[FleetAdministrativeEvidence, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("audit export limit is outside the supported range")
        authorized: list[FleetAdministrativeEvidence] = []
        for record in self._journal.list_records():
            scope = ScopeBinding(
                tenant_id=record.tenant_id,
                workspace_id=record.workspace_id,
            )
            if principal.authorizes(scope):
                authorized.append(record)
        authorized.sort(key=lambda item: (item.occurred_at_utc, item.evidence_id))
        return tuple(authorized[-limit:])

    @staticmethod
    def _validate_action_inputs(
        *,
        action: FleetAdminAction,
        replacement_enrollment_id: str | None,
        overlap_expires_at_utc: datetime | None,
    ) -> None:
        if action is FleetAdminAction.BEGIN_ROTATION and (
            replacement_enrollment_id is None or overlap_expires_at_utc is None
        ):
            raise ValueError(
                "credential rotation requires replacement enrollment and overlap expiry"
            )


class SQLiteFleetAdminMutationJournal:
    """Restart-safe single-node C3A reference journal.

    SQLite is deliberately not presented as the C3 multi-replica production store.
    The journal contract is intended to be implemented by the shared transactional
    production datastore in C3B.
    """

    provider_name = "sqlite"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self.path,
            timeout=10.0,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def reserve(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        now: datetime,
    ) -> FleetMutationResult | None:
        self._require_sha256(idempotency_key_sha256, "idempotency key hash")
        self._require_sha256(request_fingerprint_sha256, "request fingerprint")
        created_at = _iso(now)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT request_fingerprint_sha256, status, result_json
                    FROM fleet_admin_mutations
                    WHERE actor_subject = ? AND idempotency_key_sha256 = ?
                    """,
                    (actor_subject, idempotency_key_sha256),
                ).fetchone()
                if row is None:
                    self._connection.execute(
                        """
                        INSERT INTO fleet_admin_mutations (
                            actor_subject,
                            idempotency_key_sha256,
                            request_fingerprint_sha256,
                            status,
                            result_json,
                            administrative_evidence_id,
                            created_at_utc,
                            committed_at_utc
                        ) VALUES (?, ?, ?, 'pending', NULL, NULL, ?, NULL)
                        """,
                        (
                            actor_subject,
                            idempotency_key_sha256,
                            request_fingerprint_sha256,
                            created_at,
                        ),
                    )
                    self._connection.commit()
                    return None

                retained_fingerprint = str(row["request_fingerprint_sha256"])
                if retained_fingerprint != request_fingerprint_sha256:
                    self._connection.rollback()
                    raise FleetAdminIdempotencyConflict(
                        "idempotency key was already used for another Fleet mutation"
                    )

                status = str(row["status"])
                if status == "pending":
                    self._connection.rollback()
                    raise FleetAdminMutationPending(
                        "prior Fleet mutation outcome is pending reconciliation"
                    )
                if status != "committed":
                    self._connection.rollback()
                    raise FleetAdminDurabilityError(
                        "stored Fleet mutation has an unsupported status"
                    )
                raw_result = row["result_json"]
                if raw_result is None:
                    self._connection.rollback()
                    raise FleetAdminDurabilityError(
                        "committed Fleet mutation is missing its retained result"
                    )
                try:
                    result = FleetMutationResult.model_validate_json(str(raw_result))
                except ValidationError as exc:
                    self._connection.rollback()
                    raise FleetAdminDurabilityError(
                        "stored Fleet mutation result failed validation"
                    ) from exc
                self._connection.commit()
                return result
            except (
                FleetAdminIdempotencyConflict,
                FleetAdminMutationPending,
                FleetAdminDurabilityError,
            ):
                raise
            except Exception:
                self._connection.rollback()
                raise

    def commit(
        self,
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        result: FleetMutationResult,
        evidence: FleetAdministrativeEvidence,
        now: datetime,
    ) -> None:
        self._validate_commit_binding(
            actor_subject=actor_subject,
            idempotency_key_sha256=idempotency_key_sha256,
            request_fingerprint_sha256=request_fingerprint_sha256,
            result=result,
            evidence=evidence,
        )
        committed_at = _iso(now)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    """
                    SELECT request_fingerprint_sha256, status, result_json,
                           administrative_evidence_id
                    FROM fleet_admin_mutations
                    WHERE actor_subject = ? AND idempotency_key_sha256 = ?
                    """,
                    (actor_subject, idempotency_key_sha256),
                ).fetchone()
                if row is None:
                    raise FleetAdminDurabilityError(
                        "Fleet mutation commit has no durable reservation"
                    )
                if str(row["request_fingerprint_sha256"]) != request_fingerprint_sha256:
                    raise FleetAdminIdempotencyConflict(
                        "idempotency reservation fingerprint changed before commit"
                    )
                status = str(row["status"])
                if status == "committed":
                    existing_result = self._validated_result(row["result_json"])
                    existing_evidence_id = str(row["administrative_evidence_id"] or "")
                    if existing_result != result or existing_evidence_id != evidence.evidence_id:
                        raise FleetAdminDurabilityError(
                            "committed Fleet mutation does not match retry commit"
                        )
                    self._connection.commit()
                    return
                if status != "pending":
                    raise FleetAdminDurabilityError(
                        "Fleet mutation reservation is not pending"
                    )

                self._connection.execute(
                    """
                    INSERT INTO fleet_admin_evidence (
                        evidence_id,
                        actor_subject,
                        tenant_id,
                        workspace_id,
                        occurred_at_utc,
                        evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.evidence_id,
                        evidence.actor_subject,
                        evidence.tenant_id,
                        evidence.workspace_id,
                        _iso(evidence.occurred_at_utc),
                        evidence.model_dump_json(),
                    ),
                )
                cursor = self._connection.execute(
                    """
                    UPDATE fleet_admin_mutations
                    SET status = 'committed',
                        result_json = ?,
                        administrative_evidence_id = ?,
                        committed_at_utc = ?
                    WHERE actor_subject = ?
                      AND idempotency_key_sha256 = ?
                      AND status = 'pending'
                      AND request_fingerprint_sha256 = ?
                    """,
                    (
                        result.model_dump_json(),
                        evidence.evidence_id,
                        committed_at,
                        actor_subject,
                        idempotency_key_sha256,
                        request_fingerprint_sha256,
                    ),
                )
                if cursor.rowcount != 1:
                    raise FleetAdminDurabilityError(
                        "Fleet mutation reservation changed before durable commit"
                    )
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def list_records(self) -> list[FleetAdministrativeEvidence]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT evidence_json
                FROM fleet_admin_evidence
                ORDER BY occurred_at_utc ASC, evidence_id ASC
                LIMIT 10000
                """
            ).fetchall()
        records: list[FleetAdministrativeEvidence] = []
        for row in rows:
            try:
                records.append(
                    FleetAdministrativeEvidence.model_validate_json(
                        str(row["evidence_json"])
                    )
                )
            except ValidationError as exc:
                raise FleetAdminDurabilityError(
                    "stored Fleet administrative evidence failed validation"
                ) from exc
        return records

    def count_pending(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS item_count FROM fleet_admin_mutations WHERE status = 'pending'"
            ).fetchone()
        return 0 if row is None else int(row["item_count"])

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS fleet_admin_mutations (
                    actor_subject TEXT NOT NULL,
                    idempotency_key_sha256 TEXT NOT NULL,
                    request_fingerprint_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'committed')),
                    result_json TEXT NULL,
                    administrative_evidence_id TEXT NULL,
                    created_at_utc TEXT NOT NULL,
                    committed_at_utc TEXT NULL,
                    PRIMARY KEY (actor_subject, idempotency_key_sha256)
                );

                CREATE TABLE IF NOT EXISTS fleet_admin_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    actor_subject TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    evidence_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_fleet_admin_evidence_scope_time
                ON fleet_admin_evidence(tenant_id, workspace_id, occurred_at_utc);
                """
            )
            self._connection.commit()

    @staticmethod
    def _require_sha256(value: str, name: str) -> None:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"invalid {name}")

    @staticmethod
    def _validated_result(raw_result: object) -> FleetMutationResult:
        if raw_result is None:
            raise FleetAdminDurabilityError(
                "committed Fleet mutation is missing its retained result"
            )
        try:
            return FleetMutationResult.model_validate_json(str(raw_result))
        except ValidationError as exc:
            raise FleetAdminDurabilityError(
                "stored Fleet mutation result failed validation"
            ) from exc

    @staticmethod
    def _validate_commit_binding(
        *,
        actor_subject: str,
        idempotency_key_sha256: str,
        request_fingerprint_sha256: str,
        result: FleetMutationResult,
        evidence: FleetAdministrativeEvidence,
    ) -> None:
        if evidence.actor_subject != actor_subject:
            raise FleetAdminDurabilityError("Fleet evidence actor does not match reservation")
        if evidence.idempotency_key_sha256 != idempotency_key_sha256:
            raise FleetAdminDurabilityError(
                "Fleet evidence idempotency hash does not match reservation"
            )
        if evidence.request_fingerprint_sha256 != request_fingerprint_sha256:
            raise FleetAdminDurabilityError(
                "Fleet evidence request fingerprint does not match reservation"
            )
        if result.administrative_evidence_id != evidence.evidence_id:
            raise FleetAdminDurabilityError("Fleet result does not reference committed evidence")
        if (
            result.device_id != evidence.device_id
            or result.enrollment_id != evidence.enrollment_id
            or result.resulting_state is not evidence.resulting_state
            or result.action is not evidence.action
        ):
            raise FleetAdminDurabilityError(
                "Fleet result and administrative evidence describe different mutations"
            )


def _iso(value: datetime) -> str:
    return normalize_time(value).isoformat().replace("+00:00", "Z")
