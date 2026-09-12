# Gate 4 resumable-prefix plan

## Proven runtime boundary

Protected-transfer reconciliation run `34676620460` on `main` at
`eaf0795ab0b5180376738bbe5a8529b2c1335c51` proved:

- source evidence entities: `99`;
- source `next_index`: `49`;
- destination evidence entities: `75`;
- destination `next_index`: `37`;
- destination evidence prefix: exact source prefix;
- destination writers fenced;
- active destination replicas: `0`;
- Gateway root entries: `5`;
- Azure writes performed: none.

The destination therefore contains valid resumable migration state. It must not
be reset, deleted, or blindly rewritten as initialization state.

## Planner contract

`scripts/azure_migration_gate4_prefix_plan.py` is intentionally read-only. It:

1. verifies the protected Gate-3 workspace and independently supplied manifest
   SHA-256;
2. verifies destination context, zero active replicas, and exact restore-identity
   RBAC scopes;
3. reads the destination Table and proves it is an exact prefix of the protected
   source payload;
4. verifies the existing approved Gateway boundary;
5. reports only the missing Table suffix.

For the currently proven state, the expected plan is 12 missing events, which is
24 missing Table rows plus a later metadata high-water update.

The planner does **not** expose an apply mode and contains no Azure write path.
Gateway root-file shape is verified, but Gateway byte equivalence is not claimed
by this planner.

## Next implementation boundary

A separately reviewed resumable writer may be designed only after this planner
is green and approved. That writer must preserve the verified prefix and must
not replace existing prefix rows merely because they are already present.

Before any future write execution, the writer must re-prove the exact prefix on
the execution head and fail closed on any divergence, active replica, RBAC
mismatch, unexpected Gateway state, protected artifact/hash mismatch, or stale
source snapshot.

No step in this document authorizes source fencing, destination writer
activation, replica scale-up, DNS/routing changes, RBAC changes, cutover, or
source decommission.
