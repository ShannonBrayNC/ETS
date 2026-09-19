# Wave 1 R0.14 — Recovery-media rebuild and evidence reattachment

**Tracking:** #901  
**Parent:** #814  
**Claim boundary:** `r0_14_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.14 proves that Edge Compact R0 can be rebuilt from independently verified recovery
media after deliberate software-volume loss/replacement without silently inventing
identity continuity, rewriting historical evidence, replaying synchronized records as
new logical events, or overstating the R0 trust posture.

The required chain is:

```text
qualified pre-rebuild state
→ preserve off-DUT evidence/proofs
→ independently verify recovery media
→ operator rebuilds exact target asset
→ independently identify rebuilt software
→ restore identity OR rotate identity with explicit binding
→ verify historical evidence
→ reattach to upstream checkpoints without replay duplication
→ restore queue/network/time/software guardrails
→ post-rebuild canary
```

## Safety boundary

The evaluator never:

- wipes or repartitions disks;
- installs an operating system;
- executes recovery media;
- restores keys;
- changes identity material;
- deletes evidence;
- performs upstream enrollment.

Recovery remains an operator/controller action. The sole evidence copy must never be
the qualification target.

## R0 trust posture

Recovery media does not upgrade R0 into a hardware-attested device.

The retained post-rebuild posture remains:

```text
identity_profile=software_volume
hardware_attested=false
secure_boot_verified=false
hardware_key_protection=false
```

## Pre-rebuild baseline

`EdgeR0RecoveryBaseline` binds the exact R0.13 evaluation and retains:

- W1-1 asset/build/artifact/configuration binding;
- current version/schema/runtime;
- device identity and signing-key IDs;
- software-volume identity-material commitment;
- local/upstream checkpoints;
- log head;
- historical record-set commitment;
- queue/storage/network/time health;
- already-synchronized record/event/idempotency/proof bindings;
- representative proofs;
- off-DUT evidence-copy commitment.

## Recovery-media provenance

`EdgeR0RecoveryMedia` retains:

- exact hardware asset target;
- image build/artifact/configuration digests;
- media-image digest;
- configuration-template digest;
- expected version/schema/runtime;
- media creation/source provenance;
- independent verification receipt;
- operator approval.

The evaluator compares the observed media digest used during rebuild to this retained
digest.

## Rebuild observation

`EdgeR0RebuildObservation` independently records:

- exact hardware asset and storage target;
- recovery-media binding;
- media boot/use receipt;
- partition/filesystem result;
- installed build/artifact/configuration/version/schema/runtime;
- resulting boot ID;
- service health;
- controller receipt;
- external observer receipt.

A controller command alone is not sufficient evidence of rebuild completion.

## Identity recovery

R0.14 supports two explicit modes.

### Restore existing identity

`restore_existing_identity` requires:

- recovered device identity ID equals the pre-rebuild identity;
- recovered signing-key ID equals the pre-rebuild key;
- recovery-material commitment equals the retained baseline commitment;
- an explicit continuity-binding receipt;
- no identity-rotation enrollment claim.

Same hardware, hostname, IP address, or MAC address does **not** prove this continuity.

### Rotate identity with binding

`rotate_identity_with_binding` requires:

- a new device identity ID;
- a new signing-key ID;
- a retained old→new identity binding;
- explicit upstream enrollment/authorization update;
- historical evidence still attributed to the original identity;
- new evidence attributed to the new identity.

Silent identity drift fails R0.14.

## Historical evidence

Two local-history outcomes are supported.

### Local history restored

The restored local historical commitment must exactly equal the retained pre-rebuild
historical commitment.

### Local history not restored

The absence must be explicit. The evaluator does not fabricate local history.
Historical upstream commitments and representative off-DUT proofs must still
independently verify.

Restoration of synchronization or identity does not rewrite historical event IDs,
proofs, or original identity attribution.

## Upstream reattachment

Every retained pre-rebuild synchronized record must reconcile by stable:

- record ID;
- event ID;
- idempotency key;
- original identity attribution;
- upstream acceptance digest;
- proof digest.

The final upstream logical commit count remains exactly one.

R0.14 fails if recovery causes:

- replay as a new logical event;
- a second logical upstream commit;
- invented upstream acknowledgement;
- changed event/idempotency identity;
- changed historical proof/acceptance binding;
- unexplained loss.

## Checkpoint semantics

The upstream checkpoint must never regress.

When local history is restored, the local checkpoint must also remain non-regressing.

When local history is intentionally not restored, the evaluator does not pretend that
the old local checkpoint was reconstructed. The limitation remains explicit while
upstream history is independently verified.

## Prior-phase guardrails

At completion:

- storage remains below the R0.8 high watermark;
- queue is clean under the R0.9 boundary;
- network is connected under R0.10;
- time quality is `trusted_synchronized` under R0.11;
- software state is unambiguous under R0.12/R0.13 semantics.

## Independent verification

The bound off-DUT verifier must verify:

1. representative pre-rebuild proof material; and
2. each reattached synchronized record proof.

## Post-rebuild canary

One new event must bind to:

- the declared identity-recovery mode;
- the actual post-rebuild identity;
- the rebuilt build SHA;
- the rebuilt configuration digest.

It must synchronize and independently verify.

## Evaluator

```bash
python3 -m ets.physical_edge_phase13 evaluate-r0-14 \
  --manifest /path/to/bench-manifest.json \
  --phase12-evaluation /path/to/r0-13-evaluation.json \
  --baseline /path/to/recovery-baseline.json \
  --media /path/to/recovery-media.json \
  --rebuild /path/to/rebuild-observation.json \
  --identity-recovery /path/to/identity-recovery.json \
  --reattachment /path/to/reattachment.json \
  --proof-receipt /path/to/pre-rebuild-proof.json \
  --proof-receipt /path/to/reattached-record-proof.json \
  --canary /path/to/post-rebuild-canary.json \
  --output /path/to/r0-14-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_14_passed=true
```

It is not a disaster-recovery completeness claim, hardware-backed key-continuity
claim, universal recovery-media compatibility claim, production-readiness claim, or
HQP-5 physical qualification result.

## Next gate

After physical R0.14 is green, proceed to **R0.15 endurance/soak**.
