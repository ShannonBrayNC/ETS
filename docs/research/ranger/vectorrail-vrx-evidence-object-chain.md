# VectorRail/VRX Acceptance as an ETS Evidence Object

## Purpose

A VectorRail/VRX laboratory qualification is not only a checklist result. It is itself an evidentiary conclusion derived from configuration identity, gate checks, dry-run trials, final-safe-state evidence, and an independent verifier result.

This integration projects a semantically valid `ranger.vectorrail-vrx-acceptance.v0.1` record into the normative ETS Evidence Object v1 model so the qualification can participate in provenance, relationship, integrity, verification, graph, custody, and federation workflows.

## Evidence Architecture mapping

The source acceptance record remains authoritative and is embedded under the namespaced extension:

`org.lanternprotocol.ranger.vectorrail-vrx-acceptance.v0.1`

The Evidence Object carries:

- identity: acceptance ID, VRX namespace, qualification evidence type;
- provenance: reviewer, VRX device identity, acceptance workflow;
- configuration identity: the qualified configuration digest;
- claims: qualification state, final safe state, configuration digest, G0-G6 results, and required dry-run outcomes;
- relationships: each gate evidence reference and dry-run trial reference becomes a `depends_on` relationship;
- integrity: deterministic digest of the complete source acceptance record, configuration digest, and independent evidence-package digest when present;
- verification: the recorded independent acceptance-verifier result;
- assertion: reviewer attribution for the qualification claim;
- extension: the complete original acceptance record and its source-record digest.

## Sealing model

Evidence Object v1 does not recursively store its own object hash inside the envelope. The VRX integration therefore uses two complementary integrity layers.

First, the complete source acceptance record is deterministically canonicalized and SHA-256 bound as `vectorrail-vrx-acceptance-record`. Any change to a consequential or descriptive source field changes this digest.

Second, the normal Evidence Object `object_hash` seals the complete outer object, including the source record extension, provenance, relationships, claims, verification record, and integrity bindings. A verifier may be supplied the expected outer hash from an ETS ledger, receipt, exchange package, or other trusted custody boundary.

This produces the chain:

`VRX configuration → gate evidence → dry-run trial evidence → acceptance verifier → qualification record → source-record digest → Evidence Object → outer object hash → ETS custody/graph/exchange`

## Verification boundary

The reverse verifier independently checks:

1. source acceptance semantic consistency;
2. recomputed source-record digest;
3. source-record integrity binding;
4. configuration-digest binding;
5. evidence-package binding when present;
6. outer Evidence Object hash when an expected hash is supplied;
7. preservation of qualification, final-safe-state, reviewer, device, and relationship identity.

A successful result establishes integrity and semantic consistency of the recorded qualification chain. It does not prove objective physical truth beyond the instrumentation, evidence sources, and observability boundary represented by the underlying trials.

## Why this matters

This closes an important Evidence Architecture loop. The physical trials are evidence objects, but the decision that a particular VRX configuration is qualified is also evidence. That higher-order conclusion now retains explicit dependencies on the evidence that justified it rather than becoming an untraceable administrative label.

In graph terms, qualification is a derived evidence node whose edges lead back to configuration identity, laboratory checks, fault-path demonstrations, and consequence-custody trials. An independent party can therefore ask not only whether VRX was marked qualified, but **what evidence the qualification depended on and whether that qualification record is still intact**.
