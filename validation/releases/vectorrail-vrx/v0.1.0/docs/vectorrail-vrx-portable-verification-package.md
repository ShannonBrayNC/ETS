# VectorRail/VRX Portable Consequence-Custody Verification Package

## Purpose

This artifact turns the VectorRail/VRX end-to-end consequence-custody demonstration into a portable, deterministic research package that another party can replay without Lantern-hosted services.

The package is intended to answer a stronger question than whether the local implementation reports success:

> Can an independent party reconstruct the same bounded conclusion from the same sealed records, Evidence Objects, dependency graph, and verifier contract?

## Package contents

A package conforming to `ranger.vectorrail-vrx-consequence-custody-package.v0.1` contains:

1. the sealed captive-actuation trial and its deterministic record digest;
2. the trial's ETS Evidence Object projection and canonical object hash;
3. the machine-verifiable VRX acceptance record and deterministic record digest;
4. the acceptance Evidence Object projection and canonical object hash;
5. the dependency edges exported from both Evidence Objects, including raw measurement-artifact dependencies and the acceptance-to-trial dependency;
6. the complete bounded consequence-custody verification receipt;
7. the independent observation groups and explicit truth/observability boundary;
8. an offline replay manifest identifying the verifier entry point and expected hashes/conclusion; and
9. a deterministic package digest over the entire package except the digest field itself.

The package therefore binds the chain:

`authority → command → physical observations → resulting state → sealed trial → trial Evidence Object → acceptance dependency → acceptance Evidence Object → independent replay receipt`

## Determinism

The builder does not insert wall-clock generation time, host identity, network state, or other non-deterministic metadata. Given identical sealed trial and acceptance inputs, it produces identical JSON-native content and the same package digest.

This makes the artifact suitable for reproducibility checks, archival comparison, dissertation review, and later clean-room verifier work.

## Offline replay

The canonical synthetic replay manifest is:

`experiments/scenarios/vectorrail-vrx-consequence-custody-replay.json`

Run it from the repository root with:

```text
python -m ets.ranger.vectorrail_consequence_custody_package \
  experiments/scenarios/vectorrail-vrx-consequence-custody-replay.json
```

The manifest deterministically seals the existing synthetic baseline trial when its fixture digest is intentionally null, builds the portable package, replays the package through the independent package verifier, and writes the resulting JSON artifact under `artifacts/vectorrail/` unless an output override is supplied.

The expected package result is:

`VERIFIED_REPLAYABLE`

The expected underlying consequence-custody result is:

`VERIFIED_CONSISTENT`

Neither conclusion requires network access.

## Verification layers

The portable verifier checks each layer independently rather than treating the outer package hash as sufficient.

- **Package integrity:** the canonical package digest must match.
- **Record binding:** the embedded trial and acceptance record digests must recompute exactly.
- **Evidence Object binding:** embedded Evidence Objects must match fresh projections and their declared canonical hashes.
- **Dependency graph binding:** exported dependency edges must equal the edges reconstructed from the Evidence Objects.
- **Replay consistency:** re-executing the end-to-end verifier must reproduce the embedded verification receipt and replay-manifest expectations.
- **Observability conservation:** the portable artifact must preserve the same independence groups and truth-claim boundary as the underlying verifier.

This layered approach is deliberate. Re-sealing a modified outer package cannot make a changed record, Evidence Object, dependency graph, verifier result, or strengthened epistemic claim valid.

## Failure vocabulary

The package verifier returns stable high-level outcomes:

- `VERIFIED_REPLAYABLE`
- `PACKAGE_INTEGRITY_FAILURE`
- `RECORD_BINDING_FAILURE`
- `OBJECT_BINDING_FAILURE`
- `DEPENDENCY_GRAPH_FAILURE`
- `REPLAY_MISMATCH`
- `OBSERVABILITY_BOUNDARY_FAILURE`

The underlying consequence-custody conclusion remains separately visible as `chain_conclusion`, so package reproducibility is never confused with the physical-event interpretation itself.

## Research significance

This increment creates a compact external-review artifact for the ETS research claim. A reviewer no longer needs to trust a screenshot, controller log, hosted API, or narrative description of the demonstration. The package carries the inputs, projections, hashes, dependency relationships, bounded result, and replay contract necessary to reproduce the verification locally.

That materially strengthens the dissertation evidence because the experiment is now both **auditable** and **replayable**.

## Claim boundary

A successful portable replay establishes that the presented evidence package is integrity-preserving, internally consistent, and reproducibly interpreted by the stated verifier contract.

It does **not** prove that a sensor was physically correct, that the observed world state was objectively true, that the electromagnetic model was correct, that the action was optimal, or that the evidence is legally sufficient for a particular use.

The package preserves that limitation as data rather than leaving it only in prose.
