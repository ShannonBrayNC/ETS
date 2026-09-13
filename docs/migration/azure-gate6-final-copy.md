# Azure migration Gate 6 final copy

Gate 6 is not complete when the source writers are merely stopped. The source must remain dark while its final protected state is captured, reconciled to the dormant destination, and independently proven equivalent.

The completion equation is:

`source fenced + fenced-source protected capture + dormant destination reconciliation + repeated Gate 5 exact equivalence = final_copy=true`

## Preconditions

Before beginning this sequence:

1. the initial Gate 4 destination restore has completed;
2. an initial Gate 5 exact-equivalence proof has passed;
3. the Gate 6 source writer fence has passed with `source_fenced=true` and `final_copy=false`;
4. source Core and Gateway ingress are disabled;
5. source Core and Gateway have zero active revisions and zero active replicas;
6. destination Core and Gateway remain dormant with zero active replicas;
7. the persistent `GATE4_OPERATOR_ROOT` is available on the protected migration runner.

## Stage A — fenced-source final capture

`Azure Migration Gate 6 Final Source Capture` runs on the protected self-hosted migration runner.

The operator supplies:

- the exact reviewed `main` commit;
- a new final-source snapshot tag;
- the exact phrase `GATE6_FINAL_CAPTURE_AUTHORIZED`.

Before retaining any protected bytes, the capture controller re-proves that both source applications have disabled ingress, no active revision, and zero replicas. It captures the source Table and Gateway state, reads the protected source state again, and requires the state to remain byte/digest stable across the capture boundary.

Protected bytes are retained only under:

`<GATE4_OPERATOR_ROOT>/final-source-snapshots/<snapshot-tag>`

No protected source bytes are uploaded as GitHub Actions artifacts. The operator records the snapshot tag and SHA-256 of `gate6-final-source-manifest.json` in the protected migration record.

A successful capture states:

- `source_fenced=true`;
- `final_copy=false`;
- source mutation was not performed;
- destination login/write was not performed.

## Stage B — dormant-destination final reconciliation

`Azure Migration Gate 6 Final Destination Reconciliation` is a separate protected mutation boundary.

The operator supplies:

- the exact reviewed `main` commit;
- the retained final-source snapshot tag;
- the exact final-source manifest SHA-256;
- a new rollback tag;
- the exact phrase `GATE6_FINAL_RECONCILIATION_AUTHORIZED`.

The controller validates the retained Gate 6 manifest and protected bytes before applying any destination mutation. It requires `source_fenced=true` and `final_copy=false`, then requires destination replicas to remain at zero.

For the Table, it preserves the exact committed destination prefix, reuses only exact already-staged rows, inserts only missing source rows, and advances metadata last. The final destination Table must equal the fenced-source Table representation exactly.

For Gateway durable state, it captures a destination rollback snapshot first, overwrites only durable files whose bytes differ, removes only the approved inert SQLite WAL sidecar pair when present, and requires exact durable file path/size/SHA-256 equality afterward.

A successful reconciliation still states `final_copy=false`. The writer is not allowed to certify itself.

## Stage C — independent final equivalence and finality assertion

`Azure Migration Gate 6 Final Equivalence` is read-only.

It performs three ordered proofs:

1. authenticate to the source with the source-transfer identity, re-prove the source is still dark, and prove the retained final-source snapshot still equals the current fenced source;
2. capture fresh ephemeral source Table/Gateway digest manifests, authenticate to the destination restore boundary, and run the existing Gate 5 exact-equivalence verifier against the still-dormant destination;
3. only after both independent proofs pass, emit a sanitized Gate 6 finality record with `source_fenced=true` and `final_copy=true`.

Ephemeral digest manifests and proof markers are removed after the run. Only the sanitized finality record is retained as a GitHub artifact.

## Failure behavior

Any unexpected source reactivation, source-state change, retained-manifest mismatch, destination replica activation, destination prefix divergence, Gateway file mismatch, RBAC mismatch, or failed Gate 5 proof blocks finality.

There is no automatic source reactivation after the source fence. Once destination writers later begin accepting authoritative writes, a stale-source rollback is prohibited unless a separately reviewed recovery procedure reconciles the state divergence first.

## Claim boundary

A Gate 6 finality PASS proves only that:

- the source writers are fenced;
- the retained final-source snapshot still matches the source;
- the dormant destination exactly matches that fenced source state;
- `final_copy=true` is justified for migration sequencing.

It does **not**:

- activate destination writers;
- change DNS, Front Door, TLS, or routing;
- prove LanternProtocol.net destination readiness;
- decommission the source;
- delete the source Key Vault or historical verification material.

Gate 7 destination activation remains a separate review and runtime authorization boundary. Production cutover remains Gate 8, and source retirement remains Gate 9.

Refs: #773, #760, #758, #759, #769, #771, #702.
