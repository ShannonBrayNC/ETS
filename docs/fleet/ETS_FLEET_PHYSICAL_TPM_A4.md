# ETS Fleet FLEET-A4 Physical TPM Qualification

Status: implementation profile
Parent: #509 / #481
Depends on: FLEET-A3 (#508)

## Purpose

FLEET-A4 proves that one physical ETS Edge R1 TPM identity can be bound to a **disabled**
Azure Device Provisioning Service individual enrollment while ETS device identity remains
canonical. It deliberately stops before any device-side DPS provisioning or IoT Hub
connection.

A4 therefore proves two bounded facts:

1. a fresh operator challenge was satisfied by the physical TPM through the existing
   nonce/PCR/AK quote harness; and
2. the EK-derived provider registration alias and canonical ETS `device_id` round-trip
   through an Azure DPS TPM enrollment created with Microsoft Entra data-plane auth.

Passing A4 does not prove device-side DPS provisioning, reconnect behavior, IoT Hub
authorization, or revocation enforcement. Those belong to FLEET-A5.

## Split-trust model

### Physical R1

Run `scripts/fleet/prepare_physical_tpm_a4.sh` on the physical R1. The script requires:

- an operator-generated 32-byte nonce;
- an existing TPM endorsement key at the selected handle;
- an existing attestation-key context and readable AK public key;
- the already-qualified ETS TPM collector and AI Witness quote scripts.

The R1 receives no Azure management credential, DPS policy key, SAS token, connection
string, or reusable shared secret. The wrapper does not create, persist, evict, clear,
or reconfigure TPM keys, hierarchies, NV state, or PCR allocation.

Example:

```bash
./scripts/fleet/prepare_physical_tpm_a4.sh \
  ~/ets-fleet-a4 \
  /run/ets/ak.ctx \
  /run/ets/ak-public.pem \
  <64-hex-operator-nonce>
```

Transfer the resulting directory to the authorized operator workstation using an
approved encrypted channel. Do not upload the private bundle to GitHub artifacts.

## Operator workstation

The operator must have:

- Python 3.11+;
- Azure CLI authenticated with Microsoft Entra (`az login`);
- `azure-iot` CLI extension version `0.30.0`;
- `Device Provisioning Service Data Contributor` at the exact DPS resource scope;
- only the narrow management-plane read needed to resolve that DPS resource.

Run:

```powershell
python ./scripts/fleet/qualify_physical_tpm_dps_a4.py `
  --bundle C:\ETS-Evidence\fleet-a4 `
  --nonce-hex <64-hex-operator-nonce> `
  --dps-name <dps-name> `
  --resource-group <resource-group> `
  --device-id <canonical-ets-device-id>
```

The tool validates the private bundle before Azure mutation. It requires:

- exact bundle checksums;
- provider alias equal to SHA-256 of the exact TPM EK public bytes;
- Base64 EK material decoding back to those exact bytes;
- exact operator nonce and nonce hash;
- a verified TPM quote result;
- TPM-possession proof without claiming broad `hardware_attested=true`.

## Azure mutation boundary

The operator tool uses only:

```text
az iot dps ... --auth-type login
```

It refuses to overwrite a pre-existing enrollment. It creates one individual TPM
enrollment with:

- enrollment/registration ID = EK-derived provider alias;
- `deviceId` = canonical ETS device identity;
- attestation type = TPM;
- provisioning status = disabled.

It then reads the enrollment back and requires all four values to match.

By default the qualification enrollment is deleted in a `finally` cleanup path. The
operator may pass `--retain-disabled` only when intentionally handing the exact disabled
enrollment into FLEET-A5. A4 never enables the enrollment.

## Retained evidence

`a4-azure-result.json` contains only sanitized identifiers, hashes, status, tool version,
and explicit non-retention declarations. It does not retain:

- raw EK bytes or Base64 EK material;
- TPM private keys;
- AK private material;
- raw quote artifacts;
- Azure bearer tokens;
- DPS policy keys;
- SAS tokens or connection strings.

The operator-private device bundle remains outside GitHub and should be destroyed after
the A5 handoff or after A4 cleanup, according to the qualification retention policy.

## Failure conditions

A4 fails closed when the nonce is stale or mismatched, bundle integrity changes, the EK
alias is inconsistent, the quote is not verified, the Azure CLI/extension version is
wrong, Entra authorization is insufficient, the DPS target does not match, an enrollment
already exists, the created enrollment is not TPM/disabled/exactly bound, or cleanup fails.

## Next gate: FLEET-A5

FLEET-A5 selects a supported DPS device client/runtime for the R1 and proves the live
sequence: explicit enable -> provision -> reconnect -> ETS quarantine/revoke -> DPS
disable/delete as appropriate -> failed reprovision/reconnect. The Azure client remains a
provider implementation detail; ETS Fleet retains canonical device identity, scope, and
lifecycle authority.
