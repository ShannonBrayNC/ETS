# ETS AI Witness Hardware Qualification Runbook

Status: pilot execution runbook  
Date: 2026-08-21

## 1. Scope

This runbook covers the first read-only qualification pass for a named physical ETS AI Witness candidate. It collects platform/TPM evidence, obtains a freshness-bound TPM quote from an already provisioned attestation key (AK), and verifies that quote on an independent verifier.

It does **not** create or clear TPM objects, change hierarchy authorization, allocate PCRs, install persistent handles, enroll the device, or activate an update.

## 2. Preconditions

Record before starting:

- chassis manufacturer/model/serial or internal asset ID;
- exact CPU, RAM, NVMe, NIC, and power-supply configuration;
- BIOS/UEFI version and configuration export if available;
- TPM manufacturer/firmware;
- frozen ETS appliance image digest and package manifest;
- operator identity and test timestamp;
- pre-provisioned AK context/handle and independently retained AK public key;
- expected PCR selection policy.

The reference OS baseline is Ubuntu Server 24.04 LTS x86-64. The current Ubuntu Noble archive packages `tpm2-tools` 5.6. Install the approved qualification image/package set before beginning; do not let package versions float during a qualification run.

## 3. Collect platform evidence

On the appliance:

```bash
sudo scripts/ai_witness/collect_platform_evidence.sh \
  /var/lib/ets-qualification/platform
```

The collector records:

- TPM fixed properties;
- supported algorithms and ECC curves;
- allocated PCR banks;
- SHA-256 PCR values;
- Secure Boot state where `mokutil` is available;
- UEFI presence;
- raw TCG boot event log when exposed by Linux;
- parsed event-log YAML when `tpm2_eventlog` is installed;
- DMI product and BIOS information where exposed;
- a SHA-256 manifest for the resulting evidence files.

Review the output before continuing. Absence of the TPM event log, SHA-256 PCR bank, P-256 capability, or usable Secure Boot evidence is a qualification finding, not an instruction to silently continue as healthy.

## 4. Generate verifier nonce

Generate the nonce on the **independent verifier**, not on the appliance being attested.

Example:

```bash
openssl rand -hex 32 > qualification-nonce.hex
```

Transfer the nonce to the appliance over the approved authenticated channel. Preserve the verifier-side original in the evidence pack.

A nonce is single-use for the qualification transaction. Reusing a prior nonce weakens replay detection and invalidates the freshness claim.

## 5. Request TPM quote

The initial pilot PCR selection is `sha256:0,2,4,7`. It is a starting profile, not a universal assertion about every Linux boot architecture. The final PCR policy must be frozen with the named OS/firmware baseline.

On the appliance:

```bash
nonce=$(tr -d '\r\n' < qualification-nonce.hex)

scripts/ai_witness/request_tpm_quote.sh \
  /var/lib/ets-qualification/quote \
  0x81010002 \
  "$nonce" \
  sha256:0,2,4,7
```

Replace `0x81010002` with the approved AK context file or persistent handle for the named device.

The output includes:

- quote message;
- quote signature;
- quoted PCR values;
- qualification nonce;
- PCR selection;
- AK context reference;
- SHA-256 hashes for the quote artifacts.

Transfer the quote directory to the independent verifier together with the enrolled AK public key. The private AK never leaves the TPM.

## 6. Verify quote independently

On the verifier:

```bash
nonce=$(tr -d '\r\n' < qualification-nonce.hex)

scripts/ai_witness/verify_tpm_quote.sh \
  ./quote \
  ./ak-public.pem \
  "$nonce" \
  sha256:0,2,4,7
```

`tpm2_checkquote` validates the quote signature and binds the supplied qualification nonce and PCR values/selection to the quote material.

A successful quote proves that the enrolled AK signed the quoted TPM attestation structure containing the supplied freshness data/PCR state. It does **not** prove that the PCR values represent an approved software/firmware state. Reference-state appraisal is the next step.

## 7. Event-log and reference-state appraisal

For measured-boot appraisal:

1. retain the raw binary TCG event log as the authoritative captured source;
2. parse/replay the event log with approved tooling;
3. confirm the reconstructed PCR state is consistent with the quoted PCR values;
4. compare measured components/events to the frozen approved reference/RIM policy;
5. record any unknown, unmeasured, unexpected, or policy-excluded event explicitly;
6. do not convert an incomplete appraisal into `healthy`.

A cryptographically valid quote with an unapproved boot state must produce an `unqualified` or `unknown` result according to policy.

## 8. Witness signing-key qualification

After platform/AK qualification, separately inspect the production Witness signing key.

Required evidence:

- TPM public object/Name;
- ECDSA P-256 signing capability;
- SHA-256 scheme compatibility;
- public-key fingerprint enrolled in Gateway/fleet state;
- object attributes showing the selected non-exportability/fixed-parent/fixed-TPM policy;
- authorization policy used for runtime signing;
- successful `record.v2` signing through `TPM2ToolsECDSASigner`;
- successful independent verification under the enrolled public key;
- negative verification using an unrelated public key;
- proof that the ETS process never receives private-key bytes.

The repository provider uses digest-input `tpm2_sign`. The selected TPM signing-key template therefore must be compatible with that operation; a restricted signing-key flow may require a TPM-produced validation ticket and must not be assumed compatible without qualification.

## 9. Negative freshness test

Repeat quote verification with a different verifier nonce without obtaining a new quote.

Expected result: verification fails.

This is required evidence that freshness is actually bound rather than merely recorded alongside the quote.

## 10. Evidence packaging

At minimum retain:

- platform collector directory and manifest;
- raw and parsed TCG event log;
- AK public key and enrolled fingerprint;
- verifier-generated nonce;
- quote message/signature/PCR output and artifact hashes;
- quote-verification output and stderr;
- reference/RIM appraisal result;
- signer-key public attributes and fingerprint;
- exact ETS Git commit/image/package hashes;
- operator/reviewer identities;
- findings, exceptions, and waiver decisions.

The final evidence pack must be hashed and independently reviewed before the hardware configuration is labeled a qualified reference appliance.

## 11. Follow-on qualification

This first-pass runbook does not replace the full appliance test plan. After TPM/boot/signer qualification, execute:

- encrypted queue/power-cut matrix;
- storage-full and corruption cases;
- signed update interruption/recovery/rollback tests;
- clock/NTS degradation and wall-clock discontinuity tests;
- runtime-adapter authentication/spoof/replay cases;
- Gateway enrollment, rotation, revocation, and bounded-offline-standing cases;
- seven-day thermal/storage/network/queue/signing soak.
