# ETS Compliance Threat Model

## Protected properties

ETS Compliance must protect:

- framework and control-pack version provenance;
- tenant/workspace/subject isolation;
- evidence-reference integrity;
- verification-state provenance;
- deterministic evaluation behavior;
- stale/conflict/unknown visibility;
- report input/result digest integrity;
- the distinction between an evidence evaluation and a certification decision.

## Threats and controls

### Cross-tenant evidence injection

Threat: evidence from another tenant or workspace is supplied to satisfy a control.

Control: every observation carries tenant/workspace/subject scope and the evaluator fails closed
on any mismatch.

### Evidence substitution

Threat: an attacker replaces an evidence reference while preserving a friendly description.

Control: observations bind ETS event/evidence identifiers and event SHA-256; production callers
must derive verification state from ETS Verify/trusted verifier output.

### Verification laundering

Threat: failed or unverified evidence is labeled as valid support.

Control: verification state is explicit; only `verified` evidence may directly satisfy or
contradict a requirement. Unverified/failed evidence results in `unknown` when it is the only
current evidence.

### Stale-evidence laundering

Threat: old evidence is reused indefinitely.

Control: freshness is declared per evidence requirement and stale evidence becomes `unknown`.
Satisfied results expose evidence-derived standing expiration.

### Conflict suppression

Threat: favorable evidence is presented while contradictory evidence is hidden.

Control: when current verified support and contradiction are both provided, the requirement is
`unknown`, with both evidence sets retained in the result. Production collection must still
address source completeness independently.

### Framework drift

Threat: a control pack silently follows a newer framework revision.

Control: framework ID, version, profile, pack ID, and pack version are explicit digest-bound
inputs.

### Policy downgrade

Threat: an evaluator quietly relaxes evidence requirements.

Control: the policy and full control pack are included in the assessment input digest. A changed
policy produces a different report basis.

### Time manipulation

Threat: future-dated evidence artificially extends standing.

Control: evidence beyond configured future skew is rejected.

### Sensitive-data amplification

Threat: Compliance becomes a secondary store for secrets/raw evidence.

Control: v1 observations are reference-oriented, attributes are scalar/bounded, and common
secret/raw-content fields are rejected. Core projection is summary-only.

### Universal-score misrepresentation

Threat: a simple percentage is used as a blanket compliance or trust claim.

Control: v1 has no score, percentage, certification, or global compliant boolean. Per-control
outcomes and reasons remain primary.

### Report tampering

Threat: a report is edited after evaluation.

Control: canonical input and result digests plus deterministic re-evaluation detect changes.
A production publication profile should additionally sign/anchor report digests.

## Residual risks

The evaluator cannot prove:

- source observation completeness;
- semantic truth of source evidence;
- correctness of a framework mapping;
- independence/competence of an assessor;
- legal or regulatory acceptance;
- effectiveness of controls outside the declared evidence policy.

Those limitations must remain visible in product claims and exported assessments.
