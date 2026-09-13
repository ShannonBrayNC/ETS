# Azure migration Gate 5 — exact destination equivalence

Tracking: #758, #702.

Gate 5 is a **read-only** proof that the dormant destination exactly matches one fresh source capture at both ETS persistence boundaries:

- Azure Table `ETSEvents`: identical metadata identity, `next_index`, entity count implied by the ETS table shape, and ordered entry/event-index pair digests;
- Gateway Azure Files state: identical durable root-file names, byte lengths, and SHA-256 values, with only the already-approved inert zero-byte WAL sidecar pair tolerated on the dormant destination.

## Workflow

`Azure Migration Gate 5 Exact Equivalence` is manual-only and uses the existing protected migration environment.

1. Authenticate with the dedicated source-transfer identity.
2. Capture an ephemeral Table digest manifest and ephemeral Gateway digest manifest from `rg-ets-live-eastus`.
3. Clear the source Azure session.
4. Authenticate with the destination-restore identity.
5. Require zero destination replicas and exact narrow restore-identity scopes.
6. Prove exact Table state.
7. Prove exact durable Gateway bytes.
8. Delete both ephemeral manifests before completion.
9. Clear the destination Azure session.

No protected payload is uploaded as a GitHub artifact.

## Claim boundary

A successful Gate 5 run proves **point-in-time exact equivalence** only.

It does **not** prove:

- that the source is fenced;
- that the source cannot advance after capture;
- that the compared copy is the final migration copy;
- destination writer activation;
- DNS/routing cutover;
- Lantern web-edge readiness; or
- source decommission readiness.

The final migration sequence therefore requires:

1. Gate 4 restore;
2. Gate 5 exact equivalence while source remains authoritative;
3. separately authorized Gate 6 source writer fence;
4. final post-fence capture/delta application if required;
5. another successful Gate 5 exact-equivalence run against the fenced source state;
6. only then consideration of destination writer activation.

## Fail-closed stages

The verifier emits only sanitized stages:

- `table_manifest`
- `replica_fence`
- `storage_discovery`
- `restore_identity_scope`
- `table_capture`
- `table_high_water`
- `table_metadata`
- `table_digest`
- `gateway_equivalence`

Any mismatch blocks progression. Underlying protected state, hashes beyond the existing ephemeral manifests, credentials, and payloads are not printed by Gate 5.
