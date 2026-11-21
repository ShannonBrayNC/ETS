from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest

from ets.connectors.enterprise.approval_bound_executor import (
    ApprovalBoundExecutor,
    ApprovalRecord,
    ExecutionRequest,
    ExecutionStatus,
    Operation,
    Principal,
    PrincipalRole,
    WriteConflictError,
    WriteReceipt,
)

BEFORE = b'{"enabled":false}'
AFTER = b'{"enabled":true}'


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


class Store:
    def __init__(self, approval: ApprovalRecord | None) -> None:
        self.approval = approval

    def get(self, approval_id: str) -> ApprovalRecord | None:
        if self.approval is not None and approval_id == self.approval.approval_id:
            return self.approval
        return None


class Target:
    def __init__(self, *, conditional: bool = True) -> None:
        self.value = BEFORE
        self.supports_conditional_write = conditional
        self.write_error: Exception | None = None
        self.receipt = WriteReceipt(applied=True)
        self.reads = 0
        self.writes = 0

    def read(self, target_id: str) -> bytes:
        self.reads += 1
        return self.value

    def conditional_write(
        self, target_id: str, payload: bytes, expected_sha256: str
    ) -> WriteReceipt:
        self.writes += 1
        if digest(self.value) != expected_sha256:
            raise WriteConflictError
        if self.write_error is not None:
            error = self.write_error
            if isinstance(error, TimeoutError):
                self.value = payload
            raise error
        if self.receipt.applied:
            self.value = payload
        return self.receipt

    def write(self, target_id: str, payload: bytes) -> WriteReceipt:
        self.writes += 1
        if self.write_error is not None:
            raise self.write_error
        if self.receipt.applied:
            self.value = payload
        return self.receipt


class Reader:
    def __init__(self, target: Target) -> None:
        self.target = target
        self.principal = Principal("reader-1", PrincipalRole.INDEPENDENT_READER)
        self.error: Exception | None = None

    def read(self, target_id: str) -> bytes:
        if self.error is not None:
            raise self.error
        return self.target.value


@pytest.fixture
def approval() -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="approval-1",
        version=3,
        authority_id="change-board",
        case_id="case-7",
        tenant_id="tenant-test",
        target_id="target-9",
        payload_sha256=digest(AFTER),
        precondition_sha256=digest(BEFORE),
        executor_id="executor-1",
        independent_reader_id="reader-1",
        expires_at=datetime(2026, 11, 21, tzinfo=UTC),
    )


@pytest.fixture
def execution_request() -> ExecutionRequest:
    return ExecutionRequest(
        approval_id="approval-1",
        approval_version=3,
        authority_id="change-board",
        case_id="case-7",
        tenant_id="tenant-test",
        target_id="target-9",
        payload=AFTER,
    )


def execute(
    approval: ApprovalRecord,
    request: ExecutionRequest,
    *,
    target: Target | None = None,
    caller: Principal | None = None,
    reader: Reader | None = None,
):
    selected_target = target or Target()
    selected_reader = reader or Reader(selected_target)
    return ApprovalBoundExecutor(Store(approval)).execute(
        request,
        caller=caller or Principal("executor-1", PrincipalRole.EXECUTOR),
        target=selected_target,
        reader=selected_reader,
        now=datetime(2026, 11, 20, tzinfo=UTC),
    )


def test_applies_conditional_write_and_requires_independent_readback(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    result = execute(approval, execution_request)

    assert result.status is ExecutionStatus.APPLIED
    assert result.reason == "independent_readback_matches"
    assert result.conditional_write_used is True
    assert result.residual_race is False
    assert result.independent_readback is True
    assert result.before_sha256 == digest(BEFORE)
    assert result.after_sha256 == digest(AFTER)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"approval_version": 2}, "approval_version_mismatch"),
        ({"authority_id": "other"}, "authority_mismatch"),
        ({"case_id": "other"}, "case_mismatch"),
        ({"tenant_id": "other"}, "tenant_mismatch"),
        ({"target_id": "other"}, "target_mismatch"),
        ({"payload": b"altered"}, "payload_mismatch"),
        ({"operation": Operation.ROLLBACK, "rollback_of": "execution-0"}, "operation_mismatch"),
    ],
)
def test_rejects_every_altered_request_binding(
    approval: ApprovalRecord,
    execution_request: ExecutionRequest,
    change: dict[str, object],
    reason: str,
) -> None:
    target = Target()
    result = execute(approval, replace(execution_request, **change), target=target)

    assert result.status is ExecutionStatus.REJECTED
    assert result.reason == reason
    assert target.reads == 0
    assert target.writes == 0


def test_rejects_expired_approval(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    expired = replace(approval, expires_at=datetime(2026, 11, 20, tzinfo=UTC))
    result = execute(expired, execution_request)

    assert result.status is ExecutionStatus.REJECTED
    assert result.reason == "approval_expired"


@pytest.mark.parametrize(
    ("caller", "reason"),
    [
        (Principal("investigator", PrincipalRole.INVESTIGATOR), "caller_is_not_executor"),
        (Principal("other", PrincipalRole.EXECUTOR), "executor_mismatch"),
        (
            Principal("executor-1", PrincipalRole.EXECUTOR, can_manage_approvals=True),
            "executor_can_manage_approvals",
        ),
    ],
)
def test_investigator_and_approval_manager_cannot_execute(
    approval: ApprovalRecord,
    execution_request: ExecutionRequest,
    caller: Principal,
    reason: str,
) -> None:
    result = execute(approval, execution_request, caller=caller)

    assert result.status is ExecutionStatus.REJECTED
    assert result.reason == reason


def test_rejects_changed_precondition(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target()
    target.value = b'{"enabled":"changed-by-someone-else"}'

    result = execute(approval, execution_request, target=target)

    assert result.status is ExecutionStatus.CONFLICT
    assert result.reason == "precondition_changed"
    assert target.writes == 0


def test_reports_conditional_write_conflict(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target()
    target.write_error = WriteConflictError()

    result = execute(approval, execution_request, target=target)

    assert result.status is ExecutionStatus.CONFLICT
    assert result.reason == "conditional_write_conflict"


def test_non_atomic_write_requires_explicit_server_side_approval(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target(conditional=False)

    rejected = execute(approval, execution_request, target=target)
    approved = execute(
        replace(approval, allow_non_atomic_write=True), execution_request, target=target
    )

    assert rejected.reason == "conditional_write_required"
    assert rejected.status is ExecutionStatus.REJECTED
    assert approved.status is ExecutionStatus.APPLIED
    assert approved.residual_race is True


def test_timeout_is_read_back_before_any_retry(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target()
    target.write_error = TimeoutError()

    result = execute(approval, execution_request, target=target)

    assert result.status is ExecutionStatus.APPLIED
    assert result.reason == "write_timeout_readback_matches"
    assert result.write_outcome_unknown is True
    assert result.independent_readback is True
    assert target.writes == 1


def test_partial_write_is_not_reported_as_applied(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target()
    target.receipt = WriteReceipt(applied=False, partial_failure=True)

    result = execute(approval, execution_request, target=target)

    assert result.status is ExecutionStatus.PARTIAL_FAILURE
    assert result.reason == "partial_write_readback_differs"
    assert result.after_sha256 == digest(BEFORE)


def test_failed_independent_readback_produces_unknown(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    target = Target()
    reader = Reader(target)
    reader.error = RuntimeError("revoked")

    result = execute(approval, execution_request, target=target, reader=reader)

    assert result.status is ExecutionStatus.UNKNOWN
    assert result.reason == "independent_readback_failed"


def test_rollback_requires_a_separate_bound_approval(
    approval: ApprovalRecord, execution_request: ExecutionRequest
) -> None:
    rollback_approval = replace(
        approval,
        operation=Operation.ROLLBACK,
        rollback_of="execution-17",
        payload_sha256=digest(BEFORE),
        precondition_sha256=digest(AFTER),
    )
    rollback_request = replace(
        execution_request,
        payload=BEFORE,
        operation=Operation.ROLLBACK,
        rollback_of="execution-17",
    )
    target = Target()
    target.value = AFTER

    result = execute(rollback_approval, rollback_request, target=target)

    assert result.status is ExecutionStatus.APPLIED
    assert target.value == BEFORE


def test_invalid_approval_boundaries_fail_closed() -> None:
    expiry = datetime.now(UTC) + timedelta(hours=1)
    common = dict(
        approval_id="a",
        version=1,
        authority_id="authority",
        case_id="case",
        tenant_id="tenant",
        target_id="target",
        payload_sha256=digest(AFTER),
        precondition_sha256=digest(BEFORE),
        executor_id="same",
        independent_reader_id="same",
        expires_at=expiry,
    )

    with pytest.raises(ValueError, match="must be separate"):
        ApprovalRecord(**common)
    with pytest.raises(ValueError, match="rollback requires"):
        ApprovalRecord(
            **{**common, "independent_reader_id": "reader", "operation": Operation.ROLLBACK}
        )
