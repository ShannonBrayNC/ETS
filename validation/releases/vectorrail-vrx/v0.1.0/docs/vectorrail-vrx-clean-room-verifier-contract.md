# VectorRail/VRX Clean-Room Verifier Contract

Status: Proposed external-validation contract  
Tracks: #723  
Depends on: #719

## 1. Purpose

This contract defines the minimum public behavior an independently authored verifier must implement to validate the portable VectorRail/VRX consequence-custody package without using Lantern-hosted services or copying the Python reference implementation.

The objective is reproducibility, not source-code equivalence. An implementation in another language may organize its code however it chooses, but it must produce the same bounded conclusions for the same package and challenge inputs.

## 2. Independence boundary

A clean-room validator may use public specifications, JSON Schemas, committed fixtures, public research documentation, and the portable package itself. The validator must not copy implementation source from `ets/ranger/` into the independent implementation.

Implementation authors and automated agents may prepare this handoff, tests, and challenge material, but they do **not** satisfy the independent-human approval gate. The final validation record must identify the human validator and disclose material conflicts of interest.

## 3. Public inputs

The verifier contract is defined by the following public artifacts:

- `schemas/ranger/vectorrail-vrx-consequence-custody-package.v0.1.schema.json`
- `schemas/ranger/electromagnetic-actuation-trial.v0.1.schema.json`
- `schemas/ranger/vectorrail-vrx-acceptance.v0.1.schema.json`
- the Evidence Object v1 public schema and canonicalization rules
- `experiments/scenarios/vectorrail-vrx-consequence-custody-replay.json`
- `experiments/scenarios/vectorrail-vrx-clean-room-challenges.v0.1.json`
- `docs/research/ranger/vectorrail-vrx-portable-verification-package.md`
- this contract

The Python reference implementation may be used only after the independent result is frozen, for comparison or debugging. It is not an input to the clean-room implementation.

## 4. Required parsing behavior

The independent verifier must:

1. decode UTF-8 strictly;
2. reject malformed JSON;
3. reject duplicate object keys rather than silently accepting the last value;
4. reject non-finite numeric values;
5. validate the outer package against its declared schema before semantic verification;
6. treat missing, malformed, or unsupported fields as explicit verification failure rather than silently substituting defaults.

## 5. Canonical hashing

For every ETS JSON digest in this handoff, the verifier must canonicalize JSON by:

- recursively preserving JSON-native scalar values;
- requiring string object keys;
- sorting object keys lexicographically;
- emitting UTF-8 JSON with no insignificant whitespace;
- using `,` and `:` as separators;
- preserving Unicode rather than ASCII escaping solely for hashing;
- rejecting NaN and infinities.

SHA-256 is then computed over those canonical UTF-8 bytes. Fields whose contract defines a `sha256:` prefix carry the lowercase hexadecimal SHA-256 value after that prefix.

The outer portable-package digest is computed over the complete package with only `package_digest` removed from the digest preimage.

## 6. Layered verification algorithm

A conforming clean-room verifier must evaluate the following layers independently and in this precedence order.

### 6.1 Package integrity

Recompute the outer package digest. A mismatch yields:

`PACKAGE_INTEGRITY_FAILURE`

No later mutation may be treated as valid merely because an attacker supplied a new outer digest.

### 6.2 Record binding

Recompute the deterministic digest for the embedded trial record and the embedded acceptance record. The trial digest preimage is the trial object with `trial_digest` omitted. The acceptance digest covers the complete acceptance record.

Any mismatch between a recomputed record digest and its declared package binding yields:

`RECORD_BINDING_FAILURE`

### 6.3 Evidence Object binding

The embedded Evidence Objects must equal the public deterministic projections of the embedded source records and their declared canonical Evidence Object hashes must match.

For the **trial Evidence Object**:

- identity evidence ID = `trial_id`;
- namespace = `urn:lantern:ranger:captive-actuation`;
- evidence type = `electromagnetic-actuation-trial`;
- version = `1`;
- created time = trial `occurred_at`;
- provenance collector/device = `apparatus_id`, source system = `ets-ranger`, workflow = `trial_id`;
- one claim is emitted for each observation whose measurement state is `KNOWN`; unknown, contradicted, indeterminate, and unavailable observations are not promoted into affirmative claims;
- each claim ID is the observation ID, subject is the apparatus ID, predicate is `actuation.<lowercase kind>`, and value carries `value`, `unit`, and `uncertainty`;
- source ancestry and raw evidence references become `DEPENDS_ON` relationships;
- the integrity binding uses the sealed trial digest without the `sha256:` prefix, scope `electromagnetic-actuation-trial-preimage`, profile `ets.ranger.electromagnetic-actuation-trial.sha256.v0.1`;
- policy references contain the authority `policy_id`;
- the complete authoritative trial is preserved under extension `org.lanternprotocol.ranger.electromagnetic-actuation-trial.v0.1` with `included_in_object_hash=true`.

For the **acceptance Evidence Object**:

- identity evidence ID = `acceptance_id`;
- namespace = `urn:lantern:ranger:vectorrail:acceptance`;
- evidence type = `vectorrail-vrx-laboratory-acceptance`;
- version = `1`;
- created time = `reviewed_at`;
- provenance collector/operator = `reviewer_id`, device = `vrx_device_id`, source system = `ets-ranger-vectorrail`, workflow = `acceptance_id`;
- claims bind qualification, final safe state, configuration digest, every gate status, and every dry-run status;
- gate evidence references and dry-run trial references become `DEPENDS_ON` relationships;
- the acceptance record digest is bound with scope `vectorrail-vrx-acceptance-record` and profile `ets.vectorrail.acceptance-record.sha256.v0.1`;
- the configuration digest is bound with scope `vectorrail-vrx-configuration` and profile `ets.vectorrail.configuration.sha256.v0.1`;
- an acceptance-evidence-package integrity binding is present when the source verifier record supplies a `sha256:` evidence-package digest;
- the reviewer assertion references the qualification claim and verifier profile;
- the complete authoritative acceptance record is preserved under extension `org.lanternprotocol.ranger.vectorrail-vrx-acceptance.v0.1` with `included_in_object_hash=true`.

A mismatch at this layer yields:

`OBJECT_BINDING_FAILURE`

### 6.4 Dependency graph

Reconstruct all `DEPENDS_ON` relationships from both Evidence Objects and compare the normalized `(source_evidence_id, relationship_type, target_evidence_ref)` tuples with `dependency_edges` in the package.

Any difference yields:

`DEPENDENCY_GRAPH_FAILURE`

### 6.5 Consequence-custody replay

Reconstruct the bounded consequence-custody result from the embedded trial and acceptance record. The replay must distinguish authority state, command state, electrical response, mechanical response, thermal response, final safe state, trial integrity, conservative evidence projection, physical-observation backing, raw-evidence binding, acceptance-to-trial dependency, and acceptance verifier state.

The baseline package must reproduce:

- chain conclusion: `VERIFIED_CONSISTENT`
- package conclusion: `VERIFIED_REPLAYABLE`

The replay result must exactly match the embedded verification receipt and replay-manifest expectations. Otherwise the package result is:

`REPLAY_MISMATCH`

## 7. Physical-observation backing rule

A command record is not proof of physical consequence. When the recorded result says a physical response was observed, the trial must contain corresponding `KNOWN` observation evidence:

- electrical `OBSERVED` requires `ACTUATION_CURRENT`;
- mechanical `OBSERVED` or `BLOCKED` requires `ARMATURE_POSITION`;
- thermal `OBSERVED` requires `TEMPERATURE`.

This rule is central to the digital-to-physical boundary. Removing the physical observation while retaining only the command must not remain a successful reconstruction.

## 8. Observability conservation

The clean-room verifier must preserve the package's epistemic limit. It must not strengthen a bounded reconstruction into a claim of objective physical truth.

The baseline report therefore retains:

`truth_claim_supported = false`

and preserves the explicit truth-claim boundary supplied by the package. Any package mutation that strengthens that claim while leaving the source evidence unchanged yields:

`OBSERVABILITY_BOUNDARY_FAILURE`

## 9. Required package outcomes

A conforming verifier supports the following stable package-level outcomes:

- `VERIFIED_REPLAYABLE`
- `PACKAGE_INTEGRITY_FAILURE`
- `RECORD_BINDING_FAILURE`
- `OBJECT_BINDING_FAILURE`
- `DEPENDENCY_GRAPH_FAILURE`
- `REPLAY_MISMATCH`
- `OBSERVABILITY_BOUNDARY_FAILURE`

Diagnostics may be richer, but they must not replace or weaken these top-level classifications.

## 10. Claim boundary

A passing clean-room replay establishes reproducible integrity, deterministic projection, dependency binding, and bounded interpretation of the presented evidence package.

It does **not** establish sensor correctness, physical truth, electromagnetic-model correctness, optimal action, legal admissibility, regulatory approval, or production safety certification.
