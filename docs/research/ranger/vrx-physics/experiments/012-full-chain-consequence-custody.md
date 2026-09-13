# Experiment 012 — Full-Chain Consequence Custody

## Purpose

Demonstrate that a bounded VRX-R0 event can be reconstructed across authority, electrical state, mechanical interaction, motion, downstream physical consequence, resulting state, evidence integrity, and independent verification.

This experiment is the closure exercise for the twelve-module VRX Physics Laboratory curriculum.

## Safety boundary

Use only the low-voltage, current-limited, enclosed, mechanically captive VRX-R0 configuration.

Do not increase energy to make faults more dramatic. Do not defeat suppression, remove positive mechanical retention, create free-launching motion, seek maximum force, or exceed established component/instrument limits.

Fault cases must be reversible, low-energy, and isolated to one intended evidence link as much as practical.

## Research question

> Can an independent verifier distinguish a nominal VRX event from controlled failures in authority, electrical consequence, mechanical consequence, sensing, physical pre-state, and retained evidence integrity using preserved raw observations, calibration/model provenance, uncertainty, and explicit acceptance rules?

## Pre-registration

Before collecting data, record:

- device/hardware identity;
- firmware/software commit;
- accepted VRX configuration;
- valid authority object format and policy rule;
- required sensor channels;
- calibration identities;
- clock/synchronization method;
- initial-state requirements;
- accepted current/position/force/thermal/vibration domains;
- model versions, including force map where used;
- derived metrics and algorithms;
- acceptance boundaries;
- uncertainty decision rule;
- instrument-limit rules;
- `INCONCLUSIVE` conditions;
- safety abort conditions;
- exact fault cases to be executed.

Do not rewrite acceptance rules after seeing the results.

## Nominal evidence chain

The nominal run should preserve enough evidence to evaluate:

`authority -> command -> switch/terminal electrical state -> current history -> magnetic/mechanical interaction -> trajectory -> terminal/structural/thermal consequence -> resulting state -> Evidence Object -> independent verifier`

Not every physical quantity must be directly measured if the protocol does not require it, but every claim must identify whether it is:

- raw observation;
- calibrated measurement;
- derived quantity;
- model prediction;
- acceptance decision.

## Required nominal observations

Where instrumented and declared mandatory, preserve:

- authority/policy object;
- command identity and timestamp;
- actuator-terminal voltage;
- actuator-branch current;
- position history;
- force history at the defined interface;
- temperature context;
- source/receiver acceleration where vibration evidence is part of the run;
- clock metadata;
- quality flags;
- calibration/version references;
- raw samples before filtering or derived processing.

## Derived quantities

Derive only with documented algorithms and preserve enough information for independent recomputation. Candidate outputs include:

- movement onset;
- velocity and acceleration;
- electrical energy;
- impulse;
- force-map prediction where used;
- overshoot and settling;
- thermal delta and cooling state;
- vibration time-domain metrics;
- spectral metrics where supported;
- final acceptance result.

## Nominal acceptance dimensions

Evaluate at least these dimensions independently:

### AUTHORITY_VALID
The command was permitted under the required identity, policy, scope, and time conditions.

### ELECTRICAL_VALID
The measured electrical response satisfies the declared nominal criteria.

### MECHANICAL_VALID
The force/motion response satisfies the declared criteria.

### RESULTING_STATE_VALID
The final physical state satisfies the declared acceptance region.

### EVIDENCE_INTEGRITY_VALID
Required hashes/signatures/provenance relationships validate.

### EVIDENCE_SUFFICIENT
Calibration, sampling, timing, range, model domain, and uncertainty are adequate for the requested conclusion.

A final `ACCEPT` requires every dimension marked mandatory by the pre-registered protocol.

## Controlled fault cases

Run one fault at a time where practical.

### F01 — Actuator disconnected

Expected distinction:

- authority may remain valid;
- command may remain valid;
- switching request may occur;
- normal branch current is absent/inconsistent;
- expected force/motion chain is not established.

Verifier should reject on electrical/physical consequence evidence rather than authority.

### F02 — Captive carriage safely blocked

Expected distinction:

- electrical response can remain present;
- interface force may be present/elevated;
- intended position change fails;
- thermal response may differ.

Verifier should distinguish electrical energization from mechanical motion.

### F03 — Position-sensor disagreement

Introduce a controlled, documented disagreement using the approved test mechanism without damaging sensors or hardware.

Expected result:

- if conflict cannot be resolved under the pre-registered corroboration/uncertainty rule, return `INCONCLUSIVE` or the declared sensor-disagreement classification;
- do not select the preferred sensor after seeing the result.

### F04 — Current outside validated nominal envelope

Use only a safe condition already within hardware ratings but outside the pre-registered nominal acceptance region where such a condition exists.

Expected result:

- physical action may occur;
- nominal evidence acceptance fails or becomes out-of-domain according to the model/acceptance rule.

Do not expand the hardware envelope for this fault.

### F05 — Thermal pre-state outside nominal starting window

Use a safe elevated pre-state already within accepted hardware operating limits but outside the nominal experiment's starting-state criterion.

Expected result:

- the event is rejected or classified as context mismatch before claims that require nominal thermal equivalence are made.

### F06 — Invalid authority with otherwise nominal physics

Keep the physical test configuration nominal while using an intentionally invalid/expired/mismatched test authority object that cannot authorize real-world action outside this laboratory protocol.

Expected result:

- physical metrics may pass;
- authority dimension fails;
- final evidence result rejects.

Core proposition:

`Physical success != evidence validity`

### F07 — Post-capture evidence modification

After a completed retained test package is hashed/signed according to the experiment protocol, modify a copied evidence field for the tamper test.

Do not alter the canonical raw capture.

Expected result:

- cryptographic/integrity verification fails on the modified copy;
- the verifier must not accept the modified physical interpretation.

## Optional bounded fault cases

Only if already supported safely by the existing apparatus and protocol:

- sensor clipping simulated/tested through recorded fixture/test data rather than exceeding sensor physical limits;
- timing metadata mismatch using synthetic/copy evidence rather than intentionally corrupting acquisition clocks during safety-critical capture;
- force-map out-of-domain request tested at the verifier layer without operating hardware outside its characterized envelope.

## Required verifier outcomes

The verifier should support at least:

- `ACCEPT`
- `REJECT_AUTHORITY`
- `REJECT_ELECTRICAL_CONSEQUENCE`
- `REJECT_MECHANICAL_CONSEQUENCE`
- `REJECT_RESULTING_STATE`
- `REJECT_INTEGRITY`
- `OUT_OF_DOMAIN`
- `INSTRUMENT_LIMITED`
- `INCONCLUSIVE`
- `INSUFFICIENT_EVIDENCE`

Names may differ in implementation, but semantic distinctions should remain.

## Independent recomputation

The review package must allow a verifier to recompute required derived values from retained inputs rather than trusting summary fields alone.

For each required derived metric, preserve:

- source raw observations;
- calibration identity;
- analysis interval/window;
- processing/filter configuration;
- algorithm/version;
- uncertainty method;
- model version/domain where applicable.

## Evidence package

A final Experiment 012 package should include or securely reference:

- pre-registered protocol;
- configuration identity;
- authority/policy evidence;
- raw observation streams;
- calibration objects;
- model artifacts;
- analysis code/version;
- derived metrics;
- uncertainty statements;
- acceptance matrix;
- Evidence Object(s);
- integrity records;
- independent verifier output;
- nominal and fault-case comparison report.

## Success criterion

Experiment 012 succeeds when the verifier can:

1. accept the nominal event for the correct reasons;
2. reject or classify each controlled fault for the correct evidentiary reason;
3. return an inconclusive/insufficient result when the data genuinely cannot support a stronger conclusion;
4. recompute the material derived claims from retained evidence;
5. distinguish physical plausibility, authorization validity, evidence sufficiency, and integrity rather than collapsing them into one flag.

The experiment does **not** succeed merely because every injected fault results in a generic `FAIL`.