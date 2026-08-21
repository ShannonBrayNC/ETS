# ETS Compliance Architecture

## Purpose

ETS Compliance sits above ETS evidence capture, verification, and preservation. It consumes
verified evidence references and applies an explicit versioned evidence policy to control
requirements.

```text
External Framework / Baseline
          |
          v
   Versioned Control Pack
          |
          +----------------------+
                                 |
ETS evidence -> ETS Verify -> Compliance observations
                                 |
                                 v
                         Deterministic evaluator
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
        Per-control results              Reproducible report
   satisfied / not_satisfied /             input/result digests
     unknown / not_observed                       |
                 |                               v
                 +----------------------> ETS derived event
```

## Trust boundaries

### Evidence producer

Produces source evidence. ETS Compliance does not assume the source is complete or truthful.

### ETS verification boundary

Determines cryptographic verification state for referenced ETS evidence. Compliance does not
reinterpret a failed cryptographic verification as valid evidence.

### Observation mapper

Associates verified evidence with one declared evidence requirement and a disposition. This is
a policy-bearing step and must be attributable to a tool/rule/person.

### Control-pack authority

Defines which evidence is sufficient for a specific framework/profile/version. It is separate
from the framework publisher and must preserve provenance.

### Evaluator

Applies deterministic rules only. It cannot silently invent controls, evidence requirements,
weights, exceptions, or framework updates.

### Decision authority

Auditors, authorizing officials, regulators, customers, or internal governance may consume the
assessment. Their decision is outside the evaluator.

## Data boundaries

Control packs contain policy.

Evidence observations contain references, digests, verification state, scope, and bounded
assessment metadata.

Assessment reports contain conclusions and reproducibility digests.

Raw evidence remains outside the Compliance service unless another explicitly governed workflow
provides it.

## Standing

Freshness is part of the evidence requirement rather than a global assumption. The evaluator
calculates when enough current evidence will cease to exist for a satisfied requirement. This
supports an explicit Standing Boundary:

- historical question: was the evidence policy satisfied when assessed?
- present-standing question: does sufficient current evidence still support that conclusion?

A new time does not mutate an old report. Re-evaluation creates a new report with a new digest.

## Failure behavior

- cross-scope input: fail closed;
- excessive future timestamp: fail closed;
- no matching evidence: `not_observed`;
- stale evidence: `unknown`;
- unverified evidence: `unknown`;
- verified contradiction: `not_satisfied`;
- verified support and contradiction: `unknown`;
- insufficient count: `unknown`.

## Interoperability

The control model is framework neutral. NIST/OSCAL is the first interoperability target because
its assessment layer already separates controls, observations, evidence, findings, risks, and
assessment plans. Framework-specific packs remain adapters/policy artifacts rather than changes
to the evaluator core.
