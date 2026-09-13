# Azure migration — Gate 6 source writer fence apply

Tracking: #760, #758, #702.

Gate 6 is the point at which the old/source Azure deployment stops being authoritative. The source must become dark before the final protected state is copied to the dormant destination.

This implementation is deliberately split from the existing read-only Gate 6 preflight. Merging this code does **not** fence the source. The protected workflow can run only from an exact reviewed `main` commit and only when the operator supplies `GATE6_SOURCE_WRITER_FENCE_AUTHORIZED` exactly.

## Dedicated identity

The workflow requires `SOURCE_FENCE_AZURE_CLIENT_ID`, separate from the read-only `SOURCE_AZURE_CLIENT_ID` transfer identity when that transfer identity is configured. The source-fence identity should receive only the permissions required to:

- read the source Container App configuration, revisions and replicas;
- disable ingress on the exact source Core and Gateway apps;
- deactivate the exact active Core and Gateway revisions;
- read the source ETS Table and Gateway Azure Files state for stability proof.

It does not require destination permissions, DNS/Front Door permissions, source resource deletion rights, or general subscription ownership.

## Fence sequence

The controller first verifies the exact Azure tenant/subscription context and reruns the Gate 6 source-boundary discovery. It fails closed unless Core and Gateway remain uniquely identifiable, each has one active revision and at least one live replica, and neither app has an event-driven scale rule that could create an unreviewed reactivation path.

After explicit authorization, the mutation sequence is monotonic:

1. disable Gateway ingress;
2. disable Core ingress;
3. wait a bounded ingress-drain interval;
4. deactivate the exact Gateway revision discovered immediately before the fence;
5. deactivate the exact Core revision discovered immediately before the fence;
6. prove both apps have ingress disabled, zero active revisions and zero replicas;
7. capture the protected ETS Table and Gateway durable-file state;
8. wait a second bounded stability interval;
9. capture the protected state again and require exact identity across the two reads.

The post-fence equality test includes the ETS Table high-water mark, entity count, metadata identity digest, every ordered entry/event-index digest, and every Gateway durable file path, byte length and SHA-256 value.

## In-flight work policy

This is a hard writer fence after a bounded ingress-drain interval. The workflow does not claim graceful completion of every process that may have been in flight at revision deactivation. Interrupted Gateway work remains subject to the later final durable-state reconciliation. The final source Table and Gateway state are captured only after both writers are dark and the protected state is stable.

That distinction is intentional: `source_fenced=true` means the source is no longer changing. It does **not** mean the final copy has already been transferred or proven equivalent.

## Failure and rollback boundary

Once mutation starts, the controller never re-enables ingress or reactivates a source revision automatically. Automatic rollback could create a split-brain writer boundary if the operator misclassified a partial fence or if later migration steps had begun.

A partial or complete Gate 6 fence therefore fails toward the dark-source side. Any source reactivation requires a separate reviewed rollback procedure that first proves the destination has not accepted authoritative writes.

## Successful result

A successful Gate 6 source-fence run may assert:

- `source_fenced=true`;
- source Core/Gateway ingress disabled;
- zero active source revisions;
- zero active source replicas;
- stable post-fence Table and Gateway state.

It must still assert `final_copy=false`.

The required continuation is:

1. capture the final protected source state after the fence;
2. apply only the final delta to the still-dormant destination;
3. repeat Gate 5 exact equivalence against the fenced source state;
4. only after that repeated Gate 5 PASS assert `final_copy=true`;
5. only then consider Gate 7 destination writer activation.

No DNS, Front Door, LanternProtocol.net, RBAC, destination-writer, or source-decommission operation is part of this Gate 6 apply workflow.
