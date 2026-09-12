# Azure migration Gateway byte-equivalence gate

## Purpose

This checkpoint proves whether the dormant destination Gateway state is byte-for-byte equivalent to a fresh read-only capture of the current source Gateway state before any Gate 4 write workflow is designed.

The proof compares every root file by:

- exact file name;
- exact byte count;
- SHA-256 digest.

It also requires the destination Container Apps to remain fenced at zero active replicas and verifies the restore identity still holds only the approved narrow Gate-4 scopes.

## Runtime shape

The manual workflow `.github/workflows/azure-migration-gateway-equivalence.yml` uses the protected `ets-azure-migration-destination-restore` environment.

1. Authenticate with the source read identity.
2. Download each source Gateway file into ephemeral runner-local storage only long enough to calculate size and SHA-256.
3. Write an ephemeral digest-only manifest under `RUNNER_TEMP`.
4. Clear the source Azure session.
5. Authenticate with the destination restore identity.
6. Re-prove zero active replicas and exact restore-identity RBAC.
7. Download each destination Gateway file into ephemeral runner-local storage and compare exact file set, size, and SHA-256 against the source digest manifest.
8. Delete the digest manifest and clear the destination Azure session.

Temporary file bytes are removed by the local temporary-directory lifecycle. No protected Gateway bytes or digest manifest are uploaded as GitHub Actions artifacts.

## Interpretation

A pass proves only that the destination Gateway bytes equal the fresh source capture at that point in time. Because the source remains unfenced, this is not a final-copy claim.

A mismatch blocks Gate 4 execution design. Do not overwrite, delete, merge, checkpoint, or otherwise reconcile the destination automatically. Investigate the divergence read-only first.

## Explicit non-authorizations

This checkpoint does not authorize or perform:

- source fencing or source mutation;
- destination Table or Gateway writes;
- destination cleanup or replacement;
- writer activation or replica scale-up;
- RBAC, identity, Graph, SharePoint, DNS, Front Door, or routing changes;
- cutover or source decommission.

Only after this proof is green and reviewed should a separately approval-gated, one-time Gate-4 execution workflow be designed around the already-reviewed suffix writer.
