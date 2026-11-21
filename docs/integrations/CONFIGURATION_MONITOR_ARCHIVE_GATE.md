# Configuration monitor archive gate v1

Status: TCM-01 contract milestone; live Microsoft configuration-monitor qualification remains
open.

`ets.microsoft.configuration_monitor_archive.v1` blocks baseline replacement until the prior
monitor state has been exported completely and its exact bytes verify. The profile binds one
tenant and monitor to a reviewed service-limit record, evaluation schedule, archive horizon,
required field sets, request authorities and separately governed emergency approvers.

## Complete archive boundary

The archive retains the monitor definition, current baseline and parameters as independent files.
The proposed baseline and reviewed decision record are retained alongside them so both baseline
digests and the decision digest are derived from exact bytes rather than copied metadata.
Runs, results and drifts are separate paginated collections. Each collection declares its complete
field set, total record count and expected page count. Pages must be contiguous and ordered,
non-final pages retain a continuation-cursor digest, the final page has no cursor, and record totals
must reconcile. An empty collection is represented by a terminal zero-record page rather than by
omission.

Every object and page has a unique path, byte length and SHA-256 digest. The gate rehashes the
supplied bytes instead of trusting an export-success flag or manifest alone. Missing files, altered
bytes, incomplete fields, missing pages, stale archives, cross-monitor evidence, or mismatched
tenant/profile identities block replacement.

## Baseline and decision binding

The replacement request and archive bind the prior baseline digest, proposed baseline digest,
decision (`repair` or `approved_standard`) and the digest of the reviewed decision record. The old
and new baselines must differ. An archive completed after the request, or one prepared for a
different decision or baseline pair, cannot authorize the change.

The profile records the documented minimum evaluation interval, maximum daily evaluations and
result-retention window. A schedule that exceeds the quota, evaluates faster than the documented
cadence, or requests history outside retention is rejected. Polling is explicitly separate from an
evaluation: freshness comes from the retained evaluation-completion time, not from a successful
status poll.

## Emergency exception

A missing archive remains blocked by default. An emergency path must be declared on the request
and carry a separate, unexpired approval that binds the same request, tenant, monitor, baseline
pair and decision. The approver must belong to the profile's emergency authority and cannot be the
requestor. The outcome is reported as `emergency_exception`, never as archive verification. The
contract does not erase the missing evidence or imply that the prior monitor history was retained.

## Claim boundary

This milestone supplies deterministic validation and positive/negative fixtures. The example
service-limit values and fields are test data, not current Microsoft limits or a supported live
resource declaration. The contract does not prove that an export API returned all server-side
records, that the retained fields are semantically sufficient for a particular Microsoft product,
or that an emergency decision was operationally justified. TCM-01 remains open until a selected
live monitor has pinned Microsoft documentation, reproducible export commands, retained positive
and negative evidence, and independent review.
