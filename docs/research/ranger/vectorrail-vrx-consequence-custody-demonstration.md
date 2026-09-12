# VectorRail/VRX End-to-End Consequence-Custody Demonstration

**Status:** Executable research artifact  
**Scope:** Low-energy, mechanically captive VectorRail/VRX laboratory envelope only  
**Purpose:** Verify the complete evidence chain across a digital command and an observed physical consequence without treating controller logs as proof of physical outcome.

## Research question

Can an independent verifier reconstruct what authority existed, what action was requested, what command was issued, what the instrumentation observed, what resulting state was recorded, how that trial participated in VRX qualification, and whether the resulting ETS Evidence Objects preserve those propositions without strengthening them?

The executable chain is:

`authority → actuator request → issued/rejected command → physical-state observations → resulting-state evidence → sealed trial → trial Evidence Object → VRX acceptance evidence → acceptance Evidence Object → independent verifier`

The implementation is intentionally evidence-only. It does not control VectorRail hardware and does not expand the approved captive laboratory safety envelope.

## Executable implementation

The cross-layer verifier is implemented in:

`ets/ranger/vectorrail_consequence_custody.py`

The architecture suite is implemented in:

`tests/architecture/test_vectorrail_vrx_end_to_end_consequence_custody.py`

It composes the existing contracts rather than inventing a parallel evidence format:

- `electromagnetic-actuation-trial.v0.1` remains the authoritative trial record;
- `electromagnetic_actuation_verifier.py` enforces consequence-custody semantics;
- `electromagnetic_actuation_evidence_adapter.py` projects only `KNOWN` observations into generic Evidence Object claims;
- raw trial artifacts are explicit `depends_on` relationships in the Evidence Object graph;
- `vectorrail-vrx-acceptance.v0.1` remains the authoritative laboratory qualification record;
- `vectorrail_acceptance_evidence.py` links the qualification to gate evidence and dry-run trial evidence;
- `vectorrail_acceptance_evidence_verifier.py` recomputes the acceptance-record digest and outer Evidence Object hash;
- the end-to-end verifier requires the acceptance Evidence Object to depend explicitly on the trial being reconstructed.

## What the independent verifier establishes

For a nominal baseline trial, the verifier requires all of the following before returning `VERIFIED_CONSISTENT`:

1. the trial digest matches the sealed trial body;
2. authorization, safety state, command state, observations, and declared results are semantically consistent;
3. every declared observed electrical, mechanical, or thermal consequence has the required physical observation backing;
4. the trial Evidence Object integrity binding matches the sealed trial digest;
5. the trial Evidence Object contains affirmative claims only for source observations whose epistemic state is `KNOWN`;
6. raw measurement artifacts referenced by the trial remain linked through `depends_on` relationships;
7. the VRX acceptance Evidence Object explicitly depends on the reconstructed trial;
8. the acceptance record remains semantically valid and integrity-bound;
9. the acceptance Evidence Object hash recomputes correctly; and
10. the independent acceptance verifier reports a qualified, final-safe-state-confirmed result.

The verifier also exposes the independent observation groups that participated in the reconstruction so the demonstration can distinguish actual corroboration from common-source derivatives.

## Bounded conclusions

The implementation uses explicit bounded conclusions rather than a generic success boolean:

- `VERIFIED_CONSISTENT` — nominal authorized trial with independently backed recorded consequences and a valid acceptance chain;
- `VERIFIED_BLOCKED_CONSEQUENCE` — command/electrical event may exist while normal mechanical response is explicitly blocked;
- `VERIFIED_FAIL_CLOSED` — request is rejected under the recorded authority/safety boundary;
- `VERIFIED_WITH_OBSERVABILITY_LIMIT` — the chain remains reconstructable but one or more observations are unavailable, unknown, or indeterminate;
- `INDETERMINATE_PHYSICAL_CONSEQUENCE` — contradictory evidence prevents an affirmative physical-consequence conclusion;
- `INTEGRITY_FAILURE` — the sealed trial body has changed;
- `SEMANTIC_INCONSISTENCY` — the stated consequence is not supported by the required observations or violates trial semantics;
- `EVIDENCE_OBJECT_FAILURE` — the Evidence Object projection does not preserve the trial integrity/projection rules;
- `EVIDENCE_BINDING_FAILURE` — raw evidence artifacts are not bound into the evidence graph;
- `ACCEPTANCE_CHAIN_FAILURE` — the VRX qualification does not validly and explicitly depend on the reconstructed trial.

These conclusions are evidence conclusions, not declarations of objective physical truth.

## Canonical demonstration

The baseline synthetic trial exercises the complete nominal chain:

`AUTHORIZED → ISSUED → current observed → captive position observed → temperature observed → final safe state confirmed → trial sealed → trial Evidence Object → VRX acceptance depends_on trial → acceptance Evidence Object → independent verification`

The test suite then attacks the chain at its important epistemic boundaries:

- a post-seal consequence edit must produce `INTEGRITY_FAILURE`;
- an issued command with no position evidence must not be accepted as proof of motion;
- removing the acceptance-to-trial dependency must produce `ACCEPTANCE_CHAIN_FAILURE`;
- degrading an observation to `NOT_AVAILABLE` must not create an affirmative Evidence Object claim and must reduce the conclusion to `VERIFIED_WITH_OBSERVABILITY_LIMIT`.

## Dissertation significance

This artifact turns the VectorRail case from a component-level qualification example into an executable cyber-physical provenance experiment. The research claim is no longer merely that ETS can hash a laboratory acceptance record. It is that the architecture can preserve and independently reconstruct a chain in which software authority crosses into a physical actuator and returns as resulting-state evidence while conserving uncertainty, dependency, integrity, and the distinction between command and consequence.

That is directly reusable for Ranger mobility, industrial actuators, robotic systems, infrastructure automation, and other cyber-physical systems because the verifier is built around proposition boundaries rather than VectorRail-specific performance assumptions.

## Truth boundary

A successful verification establishes that the identified records are integrity-preserving and semantically consistent with the recorded observations and declared acceptance state. It does not prove that a sensor was correct, that an interpretation was objectively true, that the simplified physical model was correct, or that the commanded action was optimal.

The enduring Evidence Architecture rule remains:

`command evidence ≠ consequence evidence`
