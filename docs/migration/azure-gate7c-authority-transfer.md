# Azure migration Gate 7C — destination authority transfer

Tracking: #779, #775, #763, #758.

Gate 7C is the final ETS application authority-transfer phase before public routing. It is deliberately separate from Gate 7A Core startup and Gate 7B Gateway identity readiness because the production Gateway is not a passive process: starting its normal entrypoint begins Microsoft polling, durable checkpoint progression, queue relay, and potential Core writes.

## Authority boundary

The exact authority-transfer point is the successful mutation that raises the approved destination production Gateway from `minReplicas=0` to `minReplicas=1`.

Before that mutation, the destination can still be re-fenced without creating a new authoritative history.

After that mutation, the source is stale by definition. **Do not automatically reactivate the source.** A post-activation failure must preserve destination state and enter a separately reviewed reconciliation/recovery procedure. DNS reversal is not data rollback.

## Manual execution contract

The workflow is `Azure Migration Gate 7C Destination Authority Transfer` and is `workflow_dispatch` only. It requires:

- exact authorization phrase `GATE7C_DESTINATION_AUTHORITY_TRANSFER_AUTHORIZED`;
- exact reviewed `main` commit;
- exact successful Gate 7A workflow run ID;
- exact successful Gate 7B workflow run ID;
- exact fenced-source Gate 6 manifest SHA-256;
- a successful `Azure Migration Historical Key Offline Verification` run on the exact Gate 7C commit;
- the protected destination migration environment and destination OIDC identity.

The workflow rejects the request before Azure login if any prerequisite workflow identity, status, branch, commit, artifact, manifest binding, or authorization phrase is invalid.

## Execution sequence

1. Validate Gate 7A and Gate 7B workflow runs came from `main`, completed successfully, and expose the expected artifacts.
2. Validate the historical-key offline-verification run came from the exact reviewed Gate 7C commit.
3. Download Gate 7A and Gate 7B evidence and bind both to the same Gate 6 manifest digest.
4. Log in only to the approved destination tenant/subscription.
5. Re-read destination Table and canonical durable Gateway state.
6. Require Core active and production Gateway dormant.
7. Run the Gate 7C prepare step twice and require identical high-water/state identity immediately before mutation.
8. Raise only the production Gateway to `minReplicas=1`. This is the writer-authority transfer point.
9. Execute the existing audited workload-identity qualification inside the active production Gateway and prove the exact EchoMedia `/sites/ETS` read.
10. Wait for the migrated Gateway queue to reach a quiescent, non-failed state.
11. Using the production Gateway managed identity and its normal Core scope, append one synthetic Gate 7C EvidenceEvent through `POST /api/v1/events`.
12. Read the event back and independently verify its inclusion proof both locally and through Core.
13. Require a signed PS256 destination tree head and monotonic continuation of the migrated Table lineage.
14. Re-read durable destination state and require the migrated Gateway durable file lineage to remain present.
15. Require representative historical source evidence to have passed offline verification with retained public material.
16. Emit `gate7_destination_authority_transfer_complete` with `destination_authoritative=true` only after all proofs pass.

## Failure handling

### Failure before production Gateway activation

No destination writer-authority transfer has occurred. Correct the failed prerequisite or preflight and rerun after review.

### Failure after production Gateway activation

The destination authority boundary has already been crossed. The workflow intentionally performs **no automatic source reactivation and no automatic public-routing change**. Preserve the destination Core/Gateway state and review the failure before taking any containment or reconciliation action.

If additional destination writes must be stopped, that containment action should be explicit and separately reviewed. Never treat source restart or DNS reversal as an automatic rollback mechanism.

## Evidence retained

A successful run retains only the sanitized `azure-migration-gate7-authority-transfer` artifact. It records the source manifest binding, authority-transfer time, migrated and post-transfer high-water positions, active-Gateway M365 qualification, controlled destination append/proof result, historical offline-verification result, lineage-continuity result, and the explicit nonclaims around public routing and source reactivation.

Transient Gate 7A/Gate 7B copies, active-probe output, M365 marker, and local runner reports are removed at workflow completion.

## Explicit nonclaims

Gate 7C does not:

- change Front Door, DNS, custom domains, or TLS bindings;
- cut over `lanternprotocol.net`;
- log in to or reactivate the source tenant;
- decommission any source resource;
- authorize Gate 8;
- prove the Lantern web-edge path is production-cut-over.

Gate 8 remains the coordinated ETS routing plus LanternProtocol.net custom-domain/TLS/DNS cutover boundary. Source retirement remains later and requires the ETS and Lantern tenant-exit gates to remain green through the rollback observation window.
