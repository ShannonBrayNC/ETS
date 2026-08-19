# Lantern Protocol Azure continuity copy

This directory retains a static business-continuity copy of the public Lantern Protocol website for deployment inside the existing EchoMedia ETS Azure boundary.

## Boundary

- Azure resource group: `rg-ets-live-eastus`
- Authentication: existing `ets-azure-q1` GitHub environment / workload identity
- Hosting: isolated Azure Storage static website
- ETS Core/Gateway resources: not modified
- Search indexing: disabled on the backup copy until deliberate DNS cutover

## Source provenance

The page content was reconstructed from the retained August 13, 2026 rendered Lantern Protocol production snapshot, then brought forward with the approved ETS Technical Briefing ElevenLabs project embed. The original generated CSS/JavaScript bundles were not available while `lanternprotocol.net` was unreachable, so the continuity copy uses retained content with a standalone responsive style layer.

## Partner inquiries

The original form fields and consent language are retained. Because the continuity copy is static, submission opens the visitor's email client with both designated recipients:

- `shannon.bray@echomedia.ai`
- `shannonbraync@outlook.com`

No reusable mail credential or form-processing secret is added to Azure.

## Deployment

`.github/workflows/lantern-site-backup-deploy.yml` creates or reuses a dedicated StorageV2 account in `rg-ets-live-eastus`, enables the `$web` static website container, uploads this directory, and verifies the resulting Azure endpoint.
