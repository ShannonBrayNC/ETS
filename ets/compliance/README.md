# ETS Compliance

ETS Compliance is the policy-bound control-to-evidence evaluation layer for ETS.

It answers a deliberately narrow question:

> Given this versioned control pack, this assessment scope, this evaluation policy,
> and these independently referenced ETS observations, what conclusion is justified
> for each control requirement right now?

It does **not** turn ETS evidence into an automatic compliance certification.

## v1 reference API

`ets.compliance` provides:

- versioned framework and control-pack contracts;
- evidence requirements with source, method, count, and freshness constraints;
- digest/reference-only evidence observations;
- explicit support, contradiction, and indeterminate dispositions;
- verified, unverified, and failed-verification states;
- deterministic `satisfied`, `not_satisfied`, `unknown`, and `not_observed` outcomes;
- conflict and stale-evidence handling;
- strict tenant/workspace/subject isolation;
- future-clock-skew rejection;
- evidence-derived `valid_until_utc` standing boundaries;
- deterministic input and result digests;
- reproducible report verification;
- minimized projection of the derived assessment result into ETS Core.

## Claim boundary

A `satisfied` result means the declared evidence requirements in the selected control pack
were satisfied under the selected policy at the evaluation time. It does not mean:

- an auditor or regulator has certified the system;
- the evidence source was complete;
- every relevant real-world event was observed;
- the control was effective outside the declared evidence policy;
- a legal, contractual, or regulatory conclusion is established;
- the result remains valid after its evidence standing expires.

No aggregate compliance percentage or certification field exists in the v1 report contract.

See `docs/spec/ETS_COMPLIANCE_V1.md` for normative details.
