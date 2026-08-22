# ETS Fleet Azure DPS Adapter v1

Status: Implementation profile with physical-TPM provider-alias correction
Date: 2026-08-21
Parent: #505
Physical TPM correction: #507
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

## 2. Registration identity and provider aliases

The canonical ETS `device_id` and the Azure DPS registration ID are separate identity
layers. `DeviceEnrollmentRecord.device_id` remains the ETS identity in every profile.
The DPS registration ID is a provider alias retained in
`AzureDpsRegistrationBinding`, outside the frozen enrollment record.

For X.509 individual enrollment, the v1 provider alias remains the exact ETS `device_id`
when it is legal for DPS. X.509 enrollment requires the certificate subject common name
to match the registration ID and therefore constrains this alias to 64 characters. The
normal ETS Edge form `ets-edge:<24 hex>` fits that boundary.

For TPM individual enrollment, the provider alias is not the ETS device ID. The
registration ID is the canonical lowercase SHA-256 digest of the binary endorsement-key
public blob returned by `tpm2_readpublic -o`. This matches the current Microsoft Linux
TPM provisioning procedure. The same digest is retained as the provider identity
fingerprint.

This split prevents Azure provider identifiers from overriding ETS identity while still
using the registration identity required by a physical TPM provisioning flow.

Provider bindings fail closed when:

- a DPS alias is already owned by another ETS device;
- an ETS device is silently rebound to a different provider alias;
- the DPS instance or attestation type changes;
- an X.509 alias stops matching the canonical ETS device ID;
- a TPM alias stops matching the retained EK SHA-256 fingerprint.

## 3. Staged enrollment sequence

A new provider enrollment MUST be created in DPS with provisioning status `disabled`.
The intended sequence is:

1. derive or validate the canonical ETS device identity;
2. derive the provider registration binding for the selected attestation mechanism;
3. create the DPS individual enrollment disabled using that provider alias;
4. validate the public X.509 or TPM attestation identity;
5. submit the pending record to `DeviceEnrollmentService` using server-owned scope;
6. enable the matching DPS enrollment only after the registration is approved;
7. activate the ETS enrollment;
8. authorize connections using the ETS registry plus provider evidence;
9. disable DPS immediately when ETS quarantine/revocation policy requires it.

The provider adapter exposes stage, enable, disable, and delete operations but does not
own the ETS lifecycle state machine.

## 4. X.509 profile

The adapter validates only public/non-secret identity evidence:

- DPS service identity;
- provider registration ID and canonical ETS device ID;
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

This live qualification proves the Azure X.509 control-plane and provider-mapping
boundary. It is not a physical Edge R1 attestation claim.

## 5. TPM profile

The physical TPM provider identity is rooted in the endorsement key (EK). ETS derives
the DPS registration alias by hashing the exact binary public blob obtained from the
existing EK:

```bash
tpm2_readpublic -Q -c 0x81010001 -o endorsement-key.public.tpm2b
sha256sum -b endorsement-key.public.tpm2b
```

ETS qualification does not create a missing EK, SRK, or persistent handle. If the
expected EK cannot be read, the physical qualification fails closed rather than changing
TPM ownership or key state.

The provider binding retains only:

- canonical ETS device ID;
- DPS service identity;
- EK-derived registration alias;
- EK SHA-256 fingerprint;
- attestation type and binding basis;
- binding creation time.

Raw endorsement-key material is not stored in `DeviceEnrollmentRecord` and is not
retained in public qualification evidence. The device-side collector may create an
operator-private transient copy solely to stage the DPS TPM enrollment; that copy must
be removed after use unless a separately approved retention policy applies.

DPS TPM evidence is additionally required to return the canonical ETS device ID. The
provider alias therefore cannot replace or override ETS identity or scope.

A successful TPM control-plane enrollment is not sufficient evidence of physical TPM
possession. Physical pilot qualification must separately prove a fresh nonce-bound
challenge/quote using the expected AK and PCR selection. The existing AI Witness TPM
quote harness supplies that independent proof boundary.

## 6. Physical TPM identity collector

`scripts/fleet/collect_dps_tpm_identity.sh` is a read-only preparation tool. It:

- uses `tpm2_readpublic` against an existing EK handle;
- derives the provider registration alias from SHA-256 of the output bytes;
- creates an operator-private Base64 EK public blob for transient DPS staging;
- emits a public-safe manifest containing hashes and qualification posture only;
- explicitly records `hardware_attested=false` and `fresh_quote_required=true`.

The collector does not call `tpm2_createek`, `tpm2_createprimary`, `tpm2_evictcontrol`,
`tpm2_clear`, hierarchy-changing commands, NV-definition commands, or PCR-allocation
commands.

Detailed physical preparation and quote binding are documented in
`docs/fleet/ETS_FLEET_PHYSICAL_TPM_DPS_IDENTITY_V1.md`.

## 7. Azure authentication and RBAC

GitHub Actions authenticates to Azure using OIDC workload identity. No Azure client
secret is accepted by the workflow.

DPS administrative data-plane operations use
`az iot dps enrollment ... --auth-type login` so the workflow uses its Microsoft Entra
identity instead of retrieving a DPS shared-access policy key.

The workload identity should receive only:

- the **Device Provisioning Service Data Contributor** role at the exact **DPS resource
  scope** needed for the qualification; and
- only the narrow management-plane read needed to resolve/inspect that DPS target.

Do not grant Owner or broad Contributor merely to make the qualification pass. A
custom role may further reduce permissions if the pilot requires a narrower subset of
DPS enrollment data actions.

TPM attestation protocols may internally use challenge-response credentials generated
as part of the DPS protocol. ETS does not provision, persist, or distribute a reusable
shared/SAS device credential as the Fleet identity mechanism.

## 8. Live Virtual Demo workflow

`.github/workflows/fleet-azure-dps-live-qualification.yml` is manual
`workflow_dispatch` only and runs in the protected `fleet-azure` environment.

Required protected variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ETS_FLEET_DPS_NAME`
- `ETS_FLEET_DPS_RESOURCE_GROUP`

The current workflow is deliberately X.509 Virtual Demo only. It:

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

It does not exercise or claim physical TPM provisioning.

## 9. Evidence boundary

Retained public qualification evidence may contain only bounded identity/provenance
fields such as:

- exact source SHA and workflow run ID;
- bounded DPS resource names;
- approved ETS device ID;
- provider registration alias;
- public-key, certificate, EK, or AK SHA-256 fingerprints as applicable;
- profile/custody/attestation classification;
- provider state transition sequence;
- nonce hash, PCR selection, and quote verification result for physical qualification;
- authentication-mode labels;
- explicit non-retention declarations.

It must not retain:

- device private keys;
- raw EK public material in public artifacts;
- raw certificate bytes unless a separate evidence policy explicitly requires them;
- bearer tokens;
- DPS policy keys or connection strings;
- reusable shared/SAS device credentials;
- Azure management tokens;
- customer evidence payloads.

## 10. Failure boundaries

Qualification fails closed when:

- it is not running from the approved source boundary;
- OIDC identity or required protected variables are absent;
- the DPS resource does not match the declared target subscription/resource group;
- Entra data-plane authorization is insufficient;
- the provider alias or canonical ETS device ID does not match the retained binding;
- a provider alias is reused or rebound;
- TPM EK material does not match the retained EK fingerprint;
- provisioning cannot be proven disabled at staging;
- enable/disable transitions do not round-trip correctly;
- required cleanup fails;
- sanitized evidence cannot be produced.

A failed live run establishes no provider qualification.

## 11. Next physical gate

The next live physical Fleet gate must bind one R1 device using the EK-derived provider
alias, verify a fresh nonce-bound TPM quote, stage the matching DPS enrollment disabled,
then prove controlled enable, provision/reconnect, quarantine/revocation, and failed
reconnect after revocation. That gate must retain only sanitized fingerprints/results
and must not export any device private key.

## 12. External references

- Microsoft Learn, *Create and provision IoT Edge devices at scale on Linux using a
  TPM*: current TPM2-tools procedure for reading `ek.pub`, deriving the SHA-256
  registration ID, and Base64-encoding the endorsement key.
- Microsoft Learn, *TPM Attestation with Azure DPS*: EK trust and nonce-challenge model.
- tpm2-tools, `tpm2_readpublic(1)`: public-area read semantics.
