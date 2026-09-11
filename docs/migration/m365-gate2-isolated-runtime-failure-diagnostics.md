# M365 Gate 2 isolated runtime failure diagnostics

## Purpose

The first Azure-submitted isolated Gate 2 qualification job reached a terminal `Failed` execution state. The prior wrapper threw immediately on that status, so the temporary job was deleted in `finally` before its bounded container logs were surfaced. The production Gateway was not mutated, but the post-run zero-runtime proof was skipped because the exception propagated before the final preview.

This change is diagnostic only. It does not broaden the temporary Azure mutation or the Microsoft Graph/SharePoint read boundary.

## Required behavior

On a terminal isolated-job status of `Failed`, `Stopped`, or `Degraded`:

1. Record the terminal execution status without throwing immediately.
2. Fetch a bounded tail of the qualification container logs.
3. Surface only sanitized structural diagnostics; never emit access tokens or SharePoint payloads.
4. Delete the temporary Container Apps Job in the existing mandatory cleanup path.
5. Re-run the production Gateway preview after cleanup even when qualification failed.
6. Require zero active production Gateway revisions and replicas.
7. Only after cleanup and zero-runtime proof, return/throw the sanitized qualification failure.

The production Gateway entrypoint remains disabled, no Gateway state is mounted, no RBAC mutation is introduced, and the qualification harness remains GET-only against Microsoft Graph.
