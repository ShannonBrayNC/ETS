# ETS Edge Virtual Azure Private-Origin Handoff

This operator handoff advances the hosted **Edge Virtual** demo from approved repository code to a
private Azure origin without crossing the public activation boundary.

The handoff is intentionally narrow. It publishes a qualified four-image set, verifies the retained
supply-chain manifest, deploys the private Container Apps origin from those exact immutable images,
downloads sanitized deployment evidence, and then stops.

## Command

From PowerShell 7 on an authorized operator workstation:

```powershell
pwsh ./scripts/edge_demo/Invoke-EdgeVirtualAzurePrivateOrigin.ps1
```

The script may be run outside a repository checkout because it resolves the exact `main` SHA through
GitHub. Public-safe evidence is retained beneath `$HOME/ETS-Evidence` by default.

## Prerequisites

The workstation must have authenticated `gh` and `az` CLIs. The protected GitHub environment
`edge-demo-azure` must exist and contain these variable names:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ETS_EDGE_DEMO_ACR_NAME`
- `ETS_EDGE_DEMO_ACR_RESOURCE_GROUP`
- `ETS_EDGE_DEMO_RESOURCE_GROUP`
- `ETS_EDGE_DEMO_LOCATION`

The handoff checks only that the names exist. It never prints environment variable values, access
tokens, registry credentials, bearer tokens, EasyAuth secret values, or customer identifiers.

The Azure/GitHub workload identity must already have the bounded permissions required by the Q0
publication and private-origin workflows. ACR admin credentials are not supported.

## Execution sequence

1. Verify local GitHub and Azure authentication.
2. Resolve the exact merged `main` SHA.
3. Dispatch `edge-virtual-azure-q0-images.yml` through the GitHub REST workflow-dispatch endpoint
   with `return_run_details=true`.
4. Wait for that exact run to succeed and require the run `headSha` to equal the resolved source SHA.
5. Download `edge-virtual-azure-q0-<run-id>`.
6. Require `ets.edge_virtual_azure.image_set.v1`, vulnerability gate `PASS`, credential/customer
   retention flags `false`, `linux/amd64`, and four expected immutable ACR repository digests.
7. Re-read `main`. If it advanced, fail before any Azure origin mutation and require a new run.
8. Dispatch `deploy-edge-dark-azure.yml` with `phase=origin`, the exact source SHA, and only the four
   image references taken from the qualified manifest.
9. The workflow independently checks `GITHUB_SHA == expected_source_sha` before Azure deployment.
10. Download and verify `ets.edge_virtual_azure.origin.v1`.
11. Report the sanitized Container App and managed-environment names.
12. Stop.

The GitHub workflow-dispatch REST response supplies the exact run ID, so the handoff does not infer a
run by timing or scrape logs to determine which execution belongs to the operator.

## Evidence retained

The local evidence root contains public-safe workflow artifacts only:

- Q0 image-set manifest;
- per-image immutable digest references;
- SPDX SBOMs;
- Trivy HIGH/CRITICAL reports and vulnerability counts;
- registry posture metadata that does not contain credentials;
- private-origin manifest with exact source SHA, image references, Container App/environment names,
  `public_network_access=Disabled`, `runtime_identity_count=0`, `synthetic_only=true`,
  `hardware_attested=false`, and `public_activation=false`.

No reusable authentication material is intentionally retained by this handoff.

## Fail-closed conditions

The handoff stops before origin mutation if any of the following occurs:

- GitHub or Azure CLI authentication is unavailable;
- required protected GitHub variable names are missing;
- `main` cannot be resolved to a canonical Git SHA;
- the Q0 publication run fails or uses another source SHA;
- the vulnerability gate is not `PASS`;
- any image is outside the fixed `ets/edge-demo/*` repository set or lacks a SHA-256 digest;
- the Q0 manifest and publication run disagree;
- `main` advances between Q0 publication and origin dispatch.

The origin workflow also rejects a source-SHA mismatch before Azure login/deployment input is used.

## Explicit stop boundary

This script **does not**:

- dispatch `phase=public-edge`;
- provision or read the EasyAuth client-secret value;
- create or approve a Front Door Private Link connection;
- change `edge-demo.lanternprotocol.net` DNS;
- modify `lanternprotocol.net` apex or `www`;
- expose ETS Core or Gateway;
- create an inbound management path to physical ETS Edge;
- claim that Edge Virtual is hardware-attested.

After this handoff succeeds, the next gate is Entra/EasyAuth prerequisite qualification followed by
the already-separated Front Door Premium/WAF public-edge phase. Private Link approval remains a
specific human review action, and DNS/TLS activation remains later still.

Refs #501 #500 #496 #490.
