# Gate 4 resumable suffix writer

## Purpose

This boundary adds the code needed to advance a fenced destination Table from a
previously verified exact source prefix without resetting or rewriting that
prefix. It is intentionally narrower than Gate 4 execution and does not itself
create an execution path.

The currently proven runtime state is:

- protected source: 99 entities / `next_index=49`;
- destination: 75 entities / `next_index=37`;
- destination committed evidence: exact source prefix;
- destination writers: fenced;
- active destination replicas: 0;
- protected-transfer reconciliation run: `34676620460`.

For that state, the writer would add only the 24 missing non-metadata Table rows
for events 37 through 48 and then advance the metadata high-water mark to 49.

## Safety contract

`scripts/azure_migration_gate4_suffix_writer.py` is code-only. It has no command
line entry point and this change adds no GitHub Actions execution workflow.

Before any write, the function requires all of the following:

1. the exact explicit authorization phrase;
2. protected Gate-3 workspace and manifest verification;
3. zero active destination replicas;
4. exact narrow restore-identity RBAC scopes;
5. the approved Gateway root-file boundary;
6. a destination Table whose committed state is an exact protected-source prefix;
7. every already-staged row beyond the committed high-water mark to match the
   protected source exactly.

Any unexpected, divergent, duplicate, out-of-snapshot, malformed, or ahead-of-
source destination row blocks the operation.

## Write behavior

The writer never replaces an existing committed prefix row. Missing suffix rows
are inserted with fail-if-present semantics. If a prior interrupted attempt left
exact source rows staged beyond the committed metadata high-water mark, those
rows are reused and only the remaining missing rows are inserted.

The metadata row is updated only after a fresh read proves that every protected
non-metadata source row is present exactly. A final read must then match the
protected source Table representation and manifest entity/high-water counts.

This interruption model intentionally allows a safe retry after a partial suffix
insert without deleting or replacing already-correct rows.

## Deliberately absent

This boundary does not:

- add an Actions workflow or other runtime invocation path;
- write Gateway files;
- delete destination rows or files;
- replace committed prefix rows;
- activate Core or Gateway writers;
- scale destination replicas;
- alter RBAC, Entra, Graph, SharePoint, DNS, Front Door, routing, or signing state;
- fence or mutate the source;
- claim the migration copy is final.

The authorization phrase is an operator tripwire, not a secret or security
credential. A later execution boundary must still require the protected GitHub
environment, exact reviewed head, fresh prefix proof, protected artifact/hash
verification, and separate explicit approval.

## Next boundary

After this code is independently reviewed and green, the next engineering step
is a read-only Gateway byte-equivalence proof. Only after Table writer review and
Gateway byte state are both understood should a separately reviewed one-time
Gate-4 execution workflow be designed. Execution remains a distinct
authorization boundary.
