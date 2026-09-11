# Gate 2 isolated-job safety rationale

Issue #686 records the runtime activation boundary discovered after the structural M365 Gate 2 qualification passed.

The production Gateway remains staged at zero active revisions and zero replicas. Starting its normal revision would execute `ets.gateway.container_entrypoint`, compose the hosted Microsoft Gateway, and launch polling workers that can update Gateway runtime/store state. That is intentionally outside the final read-only identity proof.

The isolated-job path therefore proves the same Gateway UAMI and immutable image without starting the Gateway entrypoint. It creates a temporary `Microsoft.App/jobs` manual job in the same managed environment, attaches the existing Gateway UAMI plus the existing dedicated ACR pull identity, runs only the audited read-only qualification harness, and deletes the job in a mandatory cleanup path.

The implementation uses direct ARM job creation rather than the Azure CLI registry helper so it cannot opportunistically add an `AcrPull` role assignment. The job has no Gateway state volume, no Core relay configuration, no ingress, one replica, zero retries, and a bounded timeout.

This implementation PR authorizes no Azure execution. Running with `-Apply` remains a separate operator authorization boundary.
