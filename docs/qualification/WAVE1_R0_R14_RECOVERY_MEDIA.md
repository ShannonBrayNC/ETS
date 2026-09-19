# Wave 1 R0.14 — Recovery-media rebuild and evidence reattachment

**Tracking:** #901
**Parent:** #814
**Claim boundary:** `r0_14_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.14 evaluates whether an operator-controlled rebuild from independently verified
recovery media returns the named Edge Compact R0 to one unambiguous supported state
without rewriting prior evidence or silently changing identity.

```text
known R0.13 state
→ off-DUT evidence and proof retention
→ independently verified recovery media
→ operator-controlled rebuild
→ independently observed installed state
→ explicit identity restore or bound rotation
→ checkpoint/idempotency reattachment
→ prior proof verification
→ post-rebuild canary
```

## Safety boundary

The evaluator never wipes or repartitions a disk, creates recovery media, boots media,
installs an operating system, restores key material, or changes the DUT. Those actions
remain separately approved controller/operator steps with an abort path and independent
observation. Never destroy the only evidence copy.

## Baseline and media provenance

`EdgeR0RebuildBaseline` binds the exact passing R0.13 evaluation, named DUT, build,
configuration, software-volume identity, checkpoints, log head, historical record-set
commitment, pending records, resource guardrails, and representative proof digests.

`EdgeR0RecoveryMedia` retains the media source, exact image/build/artifact/configuration
digests, expected runtime/schema, independent verification receipt, and operator
approval. The observed installed state must match these commitments exactly.

## Identity recovery

The mode is declared before evaluation:

- `restore_existing_identity` requires matching identity/key identifiers and an exact
  recovery-material commitment plus continuity receipt;
- `rotate_identity_with_binding` requires new identity/key identifiers, a retained
  old→new binding, explicit upstream enrollment update, and continued attribution of
  historical evidence to the old identity.

Hostname, address, or hardware reuse never establishes identity continuity. Both modes
remain `software_volume` with `hardware_attested=false`,
`secure_boot_verified=false`, and `hardware_key_protection=false`.

## Evidence reattachment

The evaluator requires:

- unchanged historical record-set commitment and pre-rebuild log head;
- explicit disclosure when local history is intentionally not restored;
- non-regressing local and upstream checkpoints;
- stable event and idempotency identifiers;
- exactly one final logical upstream commit per pending record;
- no invented upstream acknowledgement;
- independently verified pre-rebuild and reattached-record proofs;
- restored storage, queue, network, time, and software-state guardrails.

## Evaluator

```bash
python3 -m ets.physical_edge_phase13 evaluate-r0-14 \
  --manifest /path/to/bench-manifest.json \
  --phase12-evaluation /path/to/r0-13-evaluation.json \
  --baseline /path/to/rebuild-baseline.json \
  --recovery-media /path/to/recovery-media.json \
  --rebuild /path/to/rebuild-observation.json \
  --identity-recovery /path/to/identity-recovery.json \
  --reattachment /path/to/reattachment.json \
  --proof-receipt /path/to/pre-rebuild-proof.json \
  --proof-receipt /path/to/reattached-record-proof.json \
  --canary /path/to/post-rebuild-canary.json \
  --output /path/to/r0-14-evaluation.json
```

A pass remains:

```text
disposition=phase_evidence_only
r0_14_passed=true
```

It is not disaster-recovery completeness, hardware-backed key continuity, universal
media compatibility, production readiness, or HQP-5 physical qualification.

## Failure conditions

R0.14 fails on wrong media or installed-state digests, unverified target/rebuild,
silent identity drift, invalid restoration evidence, unbound rotation, lost historical
attribution, history rewrite, checkpoint regression, replay duplication, invented
acknowledgement, guardrail escape, missing proof verification, or a canary bound to the
wrong identity/build/configuration.

## Next gate

After physical R0.14 is green, proceed to **R0.15 endurance/soak**.
