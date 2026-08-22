# ETS Fleet Physical TPM DPS Identity Qualification v1

Status: Physical-pilot preparation profile
Date: 2026-08-21
Parent: #507
Depends on: #504, #506, #495, #499

## Purpose

This profile collects the public identity material needed to bind a real TPM to Azure
DPS while preserving the ETS rule that the provider alias is not ETS canonical identity.

Collection alone is **not** a hardware-attestation result. The public-safe manifest must
state `hardware_attested=false` until a fresh nonce-bound TPM quote is independently
verified.

## Device-side collection

Run on the physical pilot device:

```bash
scripts/fleet/collect_dps_tpm_identity.sh evidence/fleet-tpm-identity 0x81010001
```

The command is read-only. The EK must already exist at the selected handle. If it does
not exist, qualification fails rather than creating or persisting a replacement key.

The collector creates:

- `endorsement-key.public.tpm2b` — operator-private public EK blob;
- `endorsement-key.public.b64` — operator-private transient DPS input;
- `provider-registration-id.txt` — lowercase SHA-256 of the binary EK public blob;
- `public-manifest.json` — public-safe identity summary;
- `private-bundle.sha256` — integrity list for the local operator bundle.

The raw EK public files are not secrets, but they are durable hardware identifiers and
are treated as operator-private/customer-identifying material. The Base64/public blob
must be deleted after DPS staging unless a separately approved retention policy applies.

## Canonical identity separation

The physical device has two distinct identifiers:

- ETS `device_id`: canonical identity used by Fleet lifecycle, authorization, scope, and
  evidence composition;
- DPS TPM `registration_id`: provider alias derived as SHA-256 of the EK public blob.

The provider alias cannot change the ETS `device_id`, tenant/workspace scope, product,
profile, attestation class, or lifecycle state.

## Fresh physical attestation

After collecting provider identity, use the existing AI Witness TPM harness with a fresh
server/operator nonce:

```bash
scripts/ai_witness/request_tpm_quote.sh \
  evidence/fleet-tpm-quote \
  <AK_CONTEXT> \
  <NONCE_HEX> \
  sha256:0,2,4,7

scripts/ai_witness/verify_tpm_quote.sh \
  evidence/fleet-tpm-quote \
  <AK_PUBLIC_PEM> \
  <NONCE_HEX> \
  sha256:0,2,4,7
```

The quote and provider identity are complementary. DPS EK enrollment does not replace
the nonce/PCR/AK proof, and a valid quote does not make the DPS provider alias canonical.

## Azure staging boundary

The subsequent live operator step may read `endorsement-key.public.b64` only long enough
to create the TPM individual enrollment in disabled state. Azure administration must use
Microsoft Entra/OIDC authorization and the exact DPS resource scope; no DPS policy key,
connection string, shared device key, or SAS device credential is permitted.

Only the following may be retained as public qualification evidence:

- canonical ETS device ID when approved for the evidence package;
- DPS provider registration alias;
- EK SHA-256 fingerprint;
- AK/public identity fingerprint;
- nonce hash and PCR selection;
- quote verification result;
- provider state transitions;
- source/tool versions and timestamps;
- explicit non-retention declarations.

The raw EK public blob/Base64 file must be deleted after DPS staging, and all device
private keys must remain non-exportable.

## Exit criteria for the next live gate

A physical Fleet qualification is not complete until one R1 device proves all of:

1. EK-derived provider alias staged disabled in the expected DPS instance;
2. fresh nonce-bound TPM quote verified against the expected AK and PCR selection;
3. canonical ETS device identity and server-owned scope remain unchanged;
4. DPS provider enrollment can be enabled only after ETS approval;
5. the device provisions/reconnects successfully through the expected DPS/IoT path;
6. ETS quarantine/revocation disables provider access and reconnect fails closed;
7. retained evidence contains no raw EK material, private key, shared key, SAS token, or
   Azure management credential.
