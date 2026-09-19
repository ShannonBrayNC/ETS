# Wave 1 R0.12 — Valid software upgrade with evidence continuity

**Tracking:** #897  
**Parent:** #814  
**Claim boundary:** `r0_12_phase_evidence_not_a_physical_qualification_result`

## Objective

R0.12 proves that an approved Edge Compact R0 source build can move to one approved
target build without losing or rewriting evidence, changing the declared R0 trust
posture, or duplicating pending synchronization state.

R0.12 covers a **valid supported upgrade** only. Upgrade failure and rollback are
qualified separately in R0.13.

## Required chain

```text
qualified source build
→ retain baseline identity/evidence/pending state
→ independently verify target package
→ operator executes approved upgrade
→ migration/service restart completes
→ exact target build/configuration is observed
→ prior evidence still verifies
→ pending records reconcile exactly once
→ prior resource/network/time boundaries remain healthy
→ target-build canary independently verifies
```

## Safety boundary

The evaluator never installs software, restarts services, modifies packages, or
changes the DUT.

Upgrade execution remains an operator/controller action. The evaluator consumes
retained evidence after the action.

## Pre-upgrade baseline

Retain an `EdgeR0UpgradeBaseline` with:

- exact R0.11 evaluation binding;
- source build SHA;
- source artifact/configuration digests;
- source version;
- device identity ID;
- signing-key ID;
- `hardware_attested=false`;
- local and upstream checkpoints;
- log head;
- historical record-set commitment;
- data schema version;
- queue/storage/network/time state;
- at least one bounded pending-record case;
- representative pre-upgrade proof digests.

The pending variant is intentional. A clean empty queue is useful, but it is not a
substitute for proving upgrade continuity while synchronization state exists.

## Package provenance

Retain `EdgeR0UpgradePackage` before execution:

- source build SHA;
- target build SHA;
- target artifact/configuration digests;
- package digest;
- target product/version label;
- target data-schema version;
- migration-plan digest;
- installer-definition digest;
- independent package verification artifact;
- explicit operator approval.

The target must differ from the source.

## Upgrade execution evidence

Retain `EdgeR0UpgradeExecution` containing:

- start/end timestamps;
- package/baseline bindings;
- installer receipt;
- service stop/start receipt;
- reboot requirement and boot IDs;
- migration result;
- exact installed build/artifact/configuration/version/schema;
- resulting device/signing identities;
- preserved historical-record commitment;
- observed pre-upgrade log head;
- final local/upstream checkpoints;
- final queue/storage/network/time state.

If a reboot is declared required, the post-upgrade boot ID must differ.

## Identity and trust posture

For Edge Compact R0 the default requirement is continuity:

```text
device identity before == device identity after
signing key before == signing key after
hardware_attested remains false
```

A future intentional key rotation requires its own explicit old→new binding evidence.
R0.12 does not allow an upgrade to manufacture a stronger hardware trust claim.

## Historical evidence continuity

The evaluator fails the run if:

- the historical record-set commitment changes;
- the pre-upgrade log head cannot be observed afterward;
- the pre-upgrade log-head digest changes;
- local or upstream checkpoints regress;
- representative pre-upgrade proofs no longer verify.

Schema migration may change storage representation, but it must not rewrite the
semantic identity or cryptographic commitment of retained historical evidence.

## Pending-record continuity

Every pending record retains:

- record ID;
- event ID;
- idempotency key;
- local authoritative status.

After upgrade, each intended pending record must:

- still exist locally;
- retain its original event ID;
- retain its original idempotency key;
- produce exactly one final logical upstream commit;
- retain upstream acceptance evidence;
- have a final proof;
- be marked synchronized only when supported by that upstream result.

The final recovered-set commitment is recomputed by the evaluator.

## Prior-phase guardrails

R0.12 must remain inside already-qualified boundaries:

- storage below the R0.8 high watermark;
- queue fully reconciled after the upgrade;
- network connected under the R0.10 boundary;
- time quality restored to `trusted_synchronized` under R0.11.

Crossing those boundaries fails R0.12 rather than broadening the upgrade test.

## Independent verification

The bound off-DUT verifier must independently verify:

1. representative pre-upgrade evidence; and
2. every recovered pending record that reaches a final upstream commit.

## Target-build canary

After the target build is healthy, create one new bounded event.

The canary must bind to:

- the target build SHA;
- the target configuration digest;
- a new authoritative event/proof;
- the bound independent verifier.

## Evaluator

```bash
python3 -m ets.physical_edge_phase11 evaluate-r0-12 \
  --manifest /path/to/bench-manifest.json \
  --phase10-evaluation /path/to/r0-11-evaluation.json \
  --baseline /path/to/upgrade-baseline.json \
  --package /path/to/upgrade-package.json \
  --execution /path/to/upgrade-execution.json \
  --reconciliation /path/to/upgrade-reconciliation.json \
  --proof-receipt /path/to/pre-upgrade-proof.json \
  --proof-receipt /path/to/pending-record-proof.json \
  --canary /path/to/post-upgrade-canary.json \
  --output /path/to/r0-12-evaluation.json
```

A passing result remains:

```text
disposition=phase_evidence_only
r0_12_passed=true
```

It is not a rollback-safety claim, arbitrary-version compatibility claim, production
readiness claim, or HQP-5 physical qualification result.

## Next gate

After physical R0.12 is green, proceed to **R0.13 failed upgrade and rollback**.
