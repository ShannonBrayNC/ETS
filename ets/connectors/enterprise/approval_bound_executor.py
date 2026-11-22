"""Approval-bound configuration repair orchestration.

The executor deliberately accepts an approval identifier rather than an approval
document from the caller.  The trusted store owns all authorization bindings and
the orchestrator compares the untrusted request against every one of them before
touching the target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

PROFILE = "ets.approval_bound_execution.v1"


class Operation(StrEnum):
    REPAIR = "repair"
    ROLLBACK = "rollback"


class PrincipalRole(StrEnum):
    INVESTIGATOR = "investigator"
    EXECUTOR = "executor"
    INDEPENDENT_READER = "independent_reader"


class ExecutionStatus(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    PARTIAL_FAILURE = "partial_failure"


@dataclass(frozen=True)
class Principal:
    principal_id: str
    role: PrincipalRole
    can_manage_approvals: bool = False


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    version: int
    authority_id: str
    case_id: str
    tenant_id: str
    target_id: str
    payload_sha256: str
    precondition_sha256: str
    executor_id: str
    independent_reader_id: str
    expires_at: datetime
    operation: Operation = Operation.REPAIR
    rollback_of: str | None = None
    allow_non_atomic_write: bool = False
    profile: str = PROFILE

    def __post_init__(self) -> None:
        if self.profile != PROFILE:
            raise ValueError("unsupported approval profile")
        for name in (
            "approval_id",
            "authority_id",
            "case_id",
            "tenant_id",
            "target_id",
            "executor_id",
            "independent_reader_id",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        if self.version < 1:
            raise ValueError("approval version must be positive")
        _require_digest("payload_sha256", self.payload_sha256)
        _require_digest("precondition_sha256", self.precondition_sha256)
        if self.expires_at.tzinfo is None:
            raise ValueError("approval expiry must be timezone-aware")
        if self.executor_id == self.independent_reader_id:
            raise ValueError("executor and independent reader must be separate")
        if self.operation is Operation.ROLLBACK and not self.rollback_of:
            raise ValueError("rollback requires a separately identified prior execution")
        if self.operation is Operation.REPAIR and self.rollback_of is not None:
            raise ValueError("repair approval cannot authorize rollback")


@dataclass(frozen=True)
class ExecutionRequest:
    approval_id: str
    approval_version: int
    authority_id: str
    case_id: str
    tenant_id: str
    target_id: str
    payload: bytes
    operation: Operation = Operation.REPAIR
    rollback_of: str | None = None


@dataclass(frozen=True)
class WriteReceipt:
    applied: bool
    partial_failure: bool = False
    detail: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    reason: str
    approval_id: str
    approval_version: int | None = None
    before_sha256: str | None = None
    after_sha256: str | None = None
    conditional_write_used: bool = False
    residual_race: bool = False
    write_started: bool = False
    write_outcome_unknown: bool = False
    independent_readback: bool = False


class ApprovalStore(Protocol):
    def get(self, approval_id: str) -> ApprovalRecord | None: ...


class TargetAdapter(Protocol):
    @property
    def supports_conditional_write(self) -> bool: ...

    def read(self, target_id: str) -> bytes: ...

    def conditional_write(
        self, target_id: str, payload: bytes, expected_sha256: str
    ) -> WriteReceipt: ...

    def write(self, target_id: str, payload: bytes) -> WriteReceipt: ...


class IndependentReader(Protocol):
    @property
    def principal(self) -> Principal: ...

    def read(self, target_id: str) -> bytes: ...


class WriteConflictError(RuntimeError):
    """The target changed before the conditional write committed."""


class ApprovalBoundExecutor:
    """Execute one approved mutation and verify it with a separate reader."""

    def __init__(self, approvals: ApprovalStore) -> None:
        self._approvals = approvals

    def execute(
        self,
        request: ExecutionRequest,
        *,
        caller: Principal,
        target: TargetAdapter,
        reader: IndependentReader,
        now: datetime | None = None,
    ) -> ExecutionResult:
        approval = self._approvals.get(request.approval_id)
        if approval is None:
            return _result(request, ExecutionStatus.REJECTED, "approval_not_found")

        rejected = self._validate_bindings(request, approval, caller, reader.principal, now)
        if rejected is not None:
            return rejected

        try:
            before = target.read(approval.target_id)
        except Exception:
            return _result(
                request,
                ExecutionStatus.UNKNOWN,
                "pre_read_failed",
                approval_version=approval.version,
            )
        before_digest = _digest(before)
        if before_digest != approval.precondition_sha256:
            return _result(
                request,
                ExecutionStatus.CONFLICT,
                "precondition_changed",
                approval_version=approval.version,
                before_sha256=before_digest,
            )

        conditional = target.supports_conditional_write
        if not conditional and not approval.allow_non_atomic_write:
            return _result(
                request,
                ExecutionStatus.REJECTED,
                "conditional_write_required",
                approval_version=approval.version,
                before_sha256=before_digest,
            )

        try:
            if conditional:
                receipt = target.conditional_write(
                    approval.target_id, request.payload, approval.precondition_sha256
                )
            else:
                receipt = target.write(approval.target_id, request.payload)
        except WriteConflictError:
            return _result(
                request,
                ExecutionStatus.CONFLICT,
                "conditional_write_conflict",
                approval_version=approval.version,
                before_sha256=before_digest,
                conditional_write_used=conditional,
                residual_race=not conditional,
                write_started=True,
            )
        except TimeoutError:
            return self._after_uncertain_write(
                request, approval, reader, before_digest, conditional, "write_timeout"
            )
        except Exception:
            return self._after_uncertain_write(
                request, approval, reader, before_digest, conditional, "write_failed"
            )

        if not receipt.applied or receipt.partial_failure:
            return self._after_uncertain_write(
                request, approval, reader, before_digest, conditional, "partial_write"
            )
        return self._verify_applied(request, approval, reader, before_digest, conditional)

    @staticmethod
    def _validate_bindings(
        request: ExecutionRequest,
        approval: ApprovalRecord,
        caller: Principal,
        reader: Principal,
        now: datetime | None,
    ) -> ExecutionResult | None:
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            raise ValueError("execution time must be timezone-aware")
        if current_time >= approval.expires_at:
            return _result(request, ExecutionStatus.REJECTED, "approval_expired")
        if caller.role is not PrincipalRole.EXECUTOR:
            return _result(request, ExecutionStatus.REJECTED, "caller_is_not_executor")
        if caller.can_manage_approvals:
            return _result(request, ExecutionStatus.REJECTED, "executor_can_manage_approvals")
        if caller.principal_id != approval.executor_id:
            return _result(request, ExecutionStatus.REJECTED, "executor_mismatch")
        if reader.role is not PrincipalRole.INDEPENDENT_READER:
            return _result(request, ExecutionStatus.REJECTED, "reader_role_invalid")
        if reader.can_manage_approvals:
            return _result(request, ExecutionStatus.REJECTED, "reader_can_manage_approvals")
        if reader.principal_id != approval.independent_reader_id:
            return _result(request, ExecutionStatus.REJECTED, "reader_mismatch")
        if reader.principal_id == caller.principal_id:
            return _result(request, ExecutionStatus.REJECTED, "readback_not_independent")

        bindings: tuple[tuple[str, object, object], ...] = (
            ("approval_version", request.approval_version, approval.version),
            ("authority", request.authority_id, approval.authority_id),
            ("case", request.case_id, approval.case_id),
            ("tenant", request.tenant_id, approval.tenant_id),
            ("target", request.target_id, approval.target_id),
            ("operation", request.operation, approval.operation),
            ("rollback", request.rollback_of, approval.rollback_of),
            ("payload", _digest(request.payload), approval.payload_sha256),
        )
        for name, actual, expected in bindings:
            if actual != expected:
                return _result(request, ExecutionStatus.REJECTED, f"{name}_mismatch")
        return None

    @staticmethod
    def _verify_applied(
        request: ExecutionRequest,
        approval: ApprovalRecord,
        reader: IndependentReader,
        before_digest: str,
        conditional: bool,
    ) -> ExecutionResult:
        try:
            after_digest = _digest(reader.read(approval.target_id))
        except Exception:
            return _result(
                request,
                ExecutionStatus.UNKNOWN,
                "independent_readback_failed",
                approval_version=approval.version,
                before_sha256=before_digest,
                conditional_write_used=conditional,
                residual_race=not conditional,
                write_started=True,
            )
        if after_digest != approval.payload_sha256:
            return _result(
                request,
                ExecutionStatus.PARTIAL_FAILURE,
                "independent_readback_mismatch",
                approval_version=approval.version,
                before_sha256=before_digest,
                after_sha256=after_digest,
                conditional_write_used=conditional,
                residual_race=not conditional,
                write_started=True,
                independent_readback=True,
            )
        return _result(
            request,
            ExecutionStatus.APPLIED,
            "independent_readback_matches",
            approval_version=approval.version,
            before_sha256=before_digest,
            after_sha256=after_digest,
            conditional_write_used=conditional,
            residual_race=not conditional,
            write_started=True,
            independent_readback=True,
        )

    @staticmethod
    def _after_uncertain_write(
        request: ExecutionRequest,
        approval: ApprovalRecord,
        reader: IndependentReader,
        before_digest: str,
        conditional: bool,
        reason: str,
    ) -> ExecutionResult:
        try:
            after_digest = _digest(reader.read(approval.target_id))
        except Exception:
            return _result(
                request,
                ExecutionStatus.UNKNOWN,
                f"{reason}_readback_failed",
                approval_version=approval.version,
                before_sha256=before_digest,
                conditional_write_used=conditional,
                residual_race=not conditional,
                write_started=True,
                write_outcome_unknown=True,
            )
        status = (
            ExecutionStatus.APPLIED
            if after_digest == approval.payload_sha256
            else ExecutionStatus.PARTIAL_FAILURE
        )
        suffix = "readback_matches" if status is ExecutionStatus.APPLIED else "readback_differs"
        return _result(
            request,
            status,
            f"{reason}_{suffix}",
            approval_version=approval.version,
            before_sha256=before_digest,
            after_sha256=after_digest,
            conditional_write_used=conditional,
            residual_race=not conditional,
            write_started=True,
            write_outcome_unknown=True,
            independent_readback=True,
        )


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _require_digest(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _result(
    request: ExecutionRequest,
    status: ExecutionStatus,
    reason: str,
    **details: object,
) -> ExecutionResult:
    return ExecutionResult(
        status=status,
        reason=reason,
        approval_id=request.approval_id,
        **details,  # type: ignore[arg-type]
    )
