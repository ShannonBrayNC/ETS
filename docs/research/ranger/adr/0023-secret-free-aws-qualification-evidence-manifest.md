# ADR 0023: Use a Secret-Free Manifest for AWS Qualification Evidence Custody

- **Status:** Accepted for the R0.2 software reference
- **Date:** 2026-09-13
- **Decision owners:** ETS Ranger research program
- **Related:** #605, ADR 0016, ADR 0017, ADR 0020, ADR 0021, ADR 0022

## Context

A controlled qualification produces artifacts under different authorities and custody domains:
execution and read authorizations, verifier trust policies, capture plans, provider observations,
the composed run, and the offline finding. Shipping all of those contents inside a convenient
index would duplicate evidence, increase disclosure risk, and blur the distinction between an
artifact inventory and the independently governed originals.

Conversely, recording only filenames permits missing, duplicated, reordered, or substituted
artifacts to appear complete.

## Decision

Define a secret-free manifest containing stable run identifiers and exactly one role-tagged
canonical digest for each required artifact. The required order is fixed so duplicate, missing,
or ambiguous roles fail schema validation. Artifact canonicalization explicitly represents binary
values as base64 before hashing but never embeds those values in the manifest.

Manifest creation is permitted only after the complete qualification run verifies offline.
Manifest verification requires every separately retained original, independently replays the run,
recomputes every artifact digest, and compares the complete expected manifest.

The manifest also carries a self-digest for mutation detection. It is deliberately unsigned in
this increment and therefore does not prove authenticity unless its expected digest is retained
through an independent custody or publication channel.

## Consequences

- The inventory contains no credentials, private keys, archive bytes, provider source bytes, or
  trust material.
- Loss of any complete signed authorization, plan, trust policy, run, or finding prevents a valid
  package verification rather than being silently treated as an absent optional record.
- Role-tagged hashing prevents the same bytes from satisfying a different artifact role.
- Cross-package artifact substitution and modified inventory entries fail closed.
- The manifest does not prove permission, provider execution, completeness, physical WORM
  custody, physical outcome, or its own authenticity.
- ETS Core and Gateway behavior remain unchanged.

## Threat treatment

| Threat | Mitigation and detection | Required evidence / test |
| --- | --- | --- |
| Evidence deletion | Exact eight-role inventory; verification requires every original. | Complete package and missing-role rejection test. |
| Duplicate or role-confused artifact | Ordered enum roles and role-tagged canonical hashes. | Schema rejection for incomplete, duplicate, or reordered roles. |
| Artifact modification or substitution | Recompute each digest after full offline run replay. | Mutated-entry and cross-run tests. |
| Secret disclosure through index | Manifest stores identifiers and digests only. | Serialization test excluding private-key fixtures and archive bytes. |
| Forged manifest | Self-digest detects mutation but authenticity remains explicitly false. | Independently retained digest or future signature/custody receipt. |
| False custody or provider claim | Fixed nonclaim fields remain false. | Schema and claim-boundary tests. |

## Rejected alternatives

### Embed the complete evidence package in the manifest

Rejected because it duplicates controlled artifacts and can disclose archive/provider evidence or
trust configuration to parties that need only an inventory.

### Inventory filenames without content digests

Rejected because names do not bind content or prevent cross-package substitution.

### Claim authenticity from a self-digest

Rejected because anyone who can replace an unsigned manifest can also recompute its digest.
