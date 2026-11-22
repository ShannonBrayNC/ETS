# Approval-bound disposable executor profile

Status: bounded EXEC-01 contract milestone; not live Microsoft qualification.

`ets.approval_bound_execution.v1` enforces one separately approved repair or rollback against a disposable target. The caller supplies only an approval identifier plus the proposed operation. A trusted server-side store supplies the authoritative version, authority, case, tenant, target, payload digest, precondition digest, executor, independent reader, operation and expiry. Any mismatch fails before a target read or write.

## Security boundary

- Only the bound executor role may invoke a write. Investigator and independent-reader roles cannot execute, and an executor with approval-management authority is rejected.
- The executor re-reads the target and hashes its exact native bytes before every attempt. A changed precondition is a conflict, not permission to replace the competing edit.
- A target adapter must use an actual conditional-write primitive when available. A pre-read is not compare-and-swap. An adapter without conditional writes is blocked unless the trusted approval explicitly accepts the residual race; the result records that limitation.
- Timeout and ambiguous failure trigger independent read-back and never an automatic write retry. A subsequent invocation repeats the pre-read and all authorization checks.
- Successful tool return is not success until the separately bound reader observes the approved payload digest. Missing or mismatched read-back is `unknown` or `partial_failure`.
- Rollback is a new `rollback` approval bound to the prior execution. Repair approval never implies rollback authority.

## Result interpretation

The result separates rejection, conflict, applied state, unknown state and partial failure. It records whether the write began, whether a conditional primitive was used, whether a residual race remains, whether the tool outcome is uncertain and whether independent read-back completed. A timeout followed by matching read-back can establish the observed target state while retaining `write_outcome_unknown=true` for the tool call itself.

The implementation uses injected target and independent-reader adapters. It does not hold Microsoft credentials, create approvals, select a production resource or establish source truth. Live EXEC-01 remains gated on qualified ID-01 identities, VER-01 evidence, the selected source/baseline gate and retained authorization/runtime evidence.
