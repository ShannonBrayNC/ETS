# ETS Fleet Azure DPS Adapter v1

Status: Implementation profile
Date: 2026-08-21
Parent: #505
Depends on: #504 / FLEET-A1 runtime

## 1. Purpose

This profile binds the provider-neutral `ets.device.enrollment.v1` runtime to Azure IoT
Hub Device Provisioning Service (DPS) without allowing Azure provider objects to become
canonical ETS device identity or authorization state.

ETS Fleet remains authoritative for:

- ETS device identity;
- tenant/workspace scope;
- enrollment lifecycle;
- credential rotation and supersession;
- quarantine/revocation/decommission state;
- authorization decisions.

Azure DPS is a provisioning and connectivity provider. Provider registration state is
additional evidence that the configured provisioning boundary matches the ETS
registration. It is not an independent source of tenant/workspace authority.

## 2. Registration identity

For v1, the Azure DPS registration ID is exactly the ETS `device_id` when the selected
attestation mechanism permits it.

This avoids a second caller-selectable identifier that could drift from the ETS
identity binding.

Azure DPS currently permits registration IDs containing case-insensitive alphanumeric
characters plus `-`, `.`, `_`, and `:`. X.509 enrollment additionally requires the
certificate subject common name to match the registration ID, and the X.509 common-name
limit constrains that registration ID to 64 characters.

The normal ETS Edge identity form `ets-edge:<24 hex>` fits this boundary.

## 3. Staged enrollment sequence

A new provider enrollment MUST be created in DPS with provisioning status `disabled`.
The intended sequence is:

1. derive or validate the ETS device identity;
2. create the DPS individual enrollment disabled;
3. validate the public X.509 or TPM attestation identity;
4. submit the pending record to `DeviceEnrollmentService` using server-owned scope;
5. enable the matching DPS enrollment only after the registration is approved;
6. activate the ETS enrollment;
7. authorize connections using the ETS registry plus provider evidence;
8. disable DPS immediately when ETS quarantine/revocation policy requires it.

The provider adapter exposes stage, enable, disable, and delete operations but does not
own the ETS lifecycle state machine.

## 4. X.509 profile

The adapter validates only public/non-secret identity evidence:

- DPS service identity;
- registration ID and device ID;
- public-key SHA-256 fingerprint;
- certificate SHA-256 thumbprint;
- trusted-chain result;
- revocation-check completion and revocation result;
- certificate validity window;
- provisioning status.

Private keys never enter the Fleet registry or retained provider result.

The live GitHub qualification creates a one-run Virtual Demo EC key and self-signed
certificate only inside the GitHub-hosted runner. The private key is removed before the
job finishes and is never uploaded. The resulting evidence explicitly records:

- `profile=virtual_demo`;
- `key_custody=software_demo`;
- `hardware_attested=false`.

This live qualification proves the Azure control-plane and identity-mapping boundary.
It is not a physical Edge R1 attestation claim.

## 5. TPM profile

The static adapter supports a production-directed TPM evidence shape containing only:

- accepted attestation state;
- ETS/DPS registration identity;
- attestation-identity SHA-256 fingerprint;
- endorsement-key SHA-256 fingerprint;
- DPS service and provisioning state.

Raw endorsement-key material and raw attestation exchanges are not retained by the ETS
record.

A successful control-plane TPM enrollment is not sufficient evidence of physical TPM
possession. Physical pilot qualification must separately prove a fresh challenge/quote
or equivalent hardware attestation from the R1 device and bind that result to the same
ETS enrollment identity.

## 6. Azure authentication and RBAC

GitHub Actions authenticates to Azure using OIDC workload identity. No Azure client
secret is accepted by the workflow.

DPS data-plane operations use `az iot dps enrollment ... --auth-type login` so the
workflow uses its Microsoft Entra identity instead of retrieving a DPS shared-access
policy key.

The workload identity should receive only:

- the **Device Provisioning Service Data Contributor** role at the exact **DPS resource
  scope** needed for the qualification; and
- only the narrow management-plane read needed to resolve/inspect that DPS target.

Do not grant Owner or broad Contributor merely to make the qualification pass. A
custom role may further reduce permissions if the pilot requires a narrower subset of
DPS enrollment data actions.

## 7. Live workflow

`.github/workflows/fleet-azure-dps-live-qualification.yml` is manual
`workflow_dispatch` only and runs in the protected `fleet-azure` environment.

Required protected variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ETS_FLEET_DPS_NAME`
- `ETS_FLEET_DPS_RESOURCE_GROUP`

The workflow:

1. requires exact merged `main` source;
2. uses Azure OIDC;
3. installs the pinned stable `azure-iot` CLI extension;
4. validates the exact DPS target;
5. creates an ephemeral Virtual Demo X.509 identity;
6. stages a disabled individual enrollment using Entra data-plane authentication;
7. verifies exact registration/device/attestation/status fields;
8. exercises enable and disable transitions;
9. deletes the qualification enrollment even when a later qualification step fails;
10. removes ephemeral key/certificate files;
11. uploads only a sanitized machine-readable manifest.

## 8. Evidence boundary

The retained manifest contains only:

- exact source SHA and workflow run ID;
- bounded DPS resource names;
- synthetic ETS device/registration ID;
- public key and certificate SHA-256 fingerprints;
- profile/custody/attestation classification;
- provider state transition sequence;
- authentication-mode labels;
- explicit non-retention declarations.

It never retains:

- device private keys;
- raw certificate bytes;
- bearer tokens;
- DPS policy keys or connection strings;
- SAS tokens;
- Azure management tokens;
- customer identifiers or evidence payloads.

## 9. Failure boundaries

The workflow fails closed when:

- it is not running from merged `main`;
- OIDC identity or required protected variables are absent;
- the DPS resource does not match the declared target subscription/resource group;
- Entra data-plane authorization is insufficient;
- created enrollment fields do not match the derived ETS identity;
- provisioning cannot be proven disabled at staging;
- enable/disable transitions do not round-trip correctly;
- cleanup fails;
- the sanitized evidence artifact cannot be produced.

A failed live run establishes no provider qualification.

## 10. Next physical gate

After this adapter and Virtual Demo control-plane qualification are merged, FLEET-A
should bind a real Edge R1 TPM/X.509 identity to the same runtime and execute a fresh
hardware-attestation challenge. That gate must retain only sanitized attestation
fingerprints/results and must not export the physical device private key.
