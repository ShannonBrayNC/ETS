# EXP-001 Scenario Corpus — Frozen Pre-Execution Design

**Status:** frozen for pre-execution review; NOT EXECUTED  
**Experiment:** EXP-001  
**Date frozen:** 2026-09-09  
**Purpose:** provide twelve semantically matched reconstruction scenarios for comparison across three representation conditions.

## Corpus rules

1. No evaluator data has been collected.
2. Each scenario below defines the substantive facts that must remain invariant across Conditions A, B, and C.
3. Condition differences may change representation semantics, labels, relation typing, verification boundaries, and explicit epistemic treatment, but must not add or remove substantive facts.
4. Every scenario contains at least two preregistered reconstruction traps.
5. Scenario identifiers, fact inventories, expected unknowns, and contradiction states are frozen before evaluator exposure.
6. Any substantive change after evaluator data is observed converts the affected analysis to exploratory under the preregistration amendment rule.

## Scenario family A — Digital / administrative

### S01 — Benefit approval with expired delegated authority

**Domain:** public-benefit administration  
**Primary traps:** identity established but authority expired; valid historical record does not establish standing.

**Facts**

- Applicant record `A-1042` was submitted at 09:14 on 3 March.
- Reviewer `R17` authenticated using a valid agency credential.
- `R17` was assigned the role `Senior Reviewer` in the directory at the time of action.
- The specific delegation permitting `R17` to approve claims above $25,000 expired at 00:00 on 1 March.
- No replacement delegation is present in the evidence package.
- `R17` approved a $31,500 claim at 10:02 on 3 March.
- The approval record is signed and its digest verifies.
- A downstream payment instruction was generated.
- No settlement confirmation is present.

**Strongest defensible reconstruction**

The approval record is authentic under the stated signature model and `R17`'s identity/role is evidenced, but authority to approve this amount at that time is not established and appears inconsistent with the expired delegation. A payment instruction was generated; payment settlement is unverified.

**Must remain unknown / unproven**

- whether another lawful authority existed outside the package;
- whether payment settled;
- whether the applicant was substantively eligible.

### S02 — Missing procurement approval record

**Domain:** procurement  
**Primary traps:** missing expected evidence; false-completeness risk.

**Facts**

- Procurement policy requires approvals from Procurement and Finance for purchases over $100,000.
- A $148,000 purchase order was issued.
- Procurement approval evidence is present and valid.
- Finance approval evidence is absent from the provided evidence package.
- The capture system reports 92% ingestion availability during the relevant two-hour interval because one connector was degraded.
- The purchase order was accepted by the vendor.
- No evidence establishes whether Finance approved through another channel.

**Strongest defensible reconstruction**

The evidence package does not contain Finance approval, but incomplete capture prevents concluding that Finance approval did not occur. The purchase order was issued and accepted by the vendor.

**Must remain unknown / unproven**

- whether Finance approval occurred outside captured channels;
- whether the purchase complied with all procurement requirements.

### S03 — Two fraud scores from one upstream source

**Domain:** administrative fraud screening  
**Primary traps:** multiple reports sharing one upstream source; inference presented beside observation.

**Facts**

- Source record `X77` contains an address mismatch.
- Model `M1` consumes `X77` and produces risk score 0.82.
- Model `M2` also consumes `X77` and produces risk score 0.79.
- `M2` additionally consumes a derived field produced from `X77`; no independent source is introduced.
- Both model outputs are signed by their service identities.
- An analyst note states, “Two independent systems confirmed fraud risk.”
- No direct evidence of fraud is present.

**Strongest defensible reconstruction**

Two model outputs support elevated risk inferences, but both materially depend on the same upstream source and therefore do not constitute two independent corroborations. Fraud itself is not directly established.

**Must remain unknown / unproven**

- whether fraud occurred;
- whether the address mismatch was erroneous or benign.

### S04 — Authentic but stale policy publication

**Domain:** regulatory publication  
**Primary traps:** cryptographically intact but stale evidence; historical record versus current standing.

**Facts**

- Policy document version 4 was signed by the authorized agency publisher on 1 May.
- Its signature and publication digest verify.
- Version 5 superseded version 4 on 10 May.
- An external recipient retrieved version 4 from a valid archival endpoint on 14 May.
- The archive receipt proves the bytes and publisher signature for version 4.
- No evidence indicates that version 4 was still operative on 14 May.

**Strongest defensible reconstruction**

Version 4 is an authentic historical publication but is stale relative to version 5 and does not establish current policy standing on 14 May.

**Must remain unknown / unproven**

- whether an exception allowed version 4 for the recipient;
- whether the recipient actually relied on the stale policy.

## Scenario family B — AI / automated systems

### S05 — AI recommendation and human authorization

**Domain:** lending/financial decision  
**Primary traps:** inference versus observation; standing separation.

**Facts**

- Model `Credit-AI-7` receives applicant data and produces recommendation `DENY` with reason code `R14`.
- The model output is recorded with model version and runtime identity.
- Policy requires a human underwriter to authorize denials above a specified exposure threshold.
- Underwriter `U9` authenticated successfully.
- `U9` possessed active underwriting authority at the relevant time.
- `U9` approved the denial after reviewing the recommendation.
- A denial notice was generated.
- No evidence proves that the notice was delivered to the applicant.

**Strongest defensible reconstruction**

The model produced a denial recommendation; an authorized human approved the denial; a notice was generated. Delivery is unverified. The model output is an inference, not direct evidence that the applicant was objectively uncreditworthy.

### S06 — Agent command accepted, execution unconfirmed

**Domain:** automated cloud operations  
**Primary traps:** command issued without execution evidence; command/result collapse.

**Facts**

- An AI operations agent identifies an account as high risk.
- Policy engine authorizes account suspension.
- The agent issues `disable-account` to the identity service.
- The identity service returns `202 Accepted` with operation ID `OP-88`.
- No completion event for `OP-88` is present.
- A later authentication attempt succeeds 90 seconds after the `202 Accepted` response.
- The authentication event is valid under the identity service's logging model.

**Strongest defensible reconstruction**

The suspension command was authorized and accepted for processing, but successful execution is not established; the later successful authentication contradicts any assumption that disablement had already taken effect.

### S07 — AI detector score on authentic capture

**Domain:** media integrity  
**Primary traps:** inference beside direct observation; epistemic overstatement.

**Facts**

- A camera signs a capture artifact using a registered device key.
- The artifact bytes match the signed digest.
- An AI synthetic-media detector produces score 0.91 for “likely synthetic.”
- Detector version and threshold are known.
- Independent review finds no additional source artifact proving whether content was staged, generated, or merely post-processed.
- The camera signature proves capture provenance under the device trust model, not scene truth.

**Strongest defensible reconstruction**

The artifact is cryptographically linked to the registered capture device; the detector produced a strong synthetic-media inference. Neither mechanism alone proves the scene's factual truth or complete origin history.

### S08 — Model output based on incomplete observation capability

**Domain:** automated safety monitoring  
**Primary traps:** incomplete observation capability; missing evidence versus event absence.

**Facts**

- Monitoring model `SafeWatch-3` receives feeds from sensors A, B, and C.
- Sensor C was offline for 11 minutes before the model decision.
- The system health record explicitly marks C unavailable.
- Model output states `NO_HAZARD_DETECTED`.
- Sensors A and B report no hazard indications.
- Sensor C is the only sensor capable of observing the east enclosure.
- No independent east-enclosure observation exists for the interval.

**Strongest defensible reconstruction**

No hazard was detected in the observed coverage of A and B. The east enclosure was unobservable during the relevant interval, so “no hazard existed anywhere” is unsupported.

## Scenario family C — Cyber-physical systems

### S09 — Ranger motion command without physical-result observation

**Domain:** mobile robotics  
**Primary traps:** command versus execution; execution versus consequence.

**Facts**

- Ranger is in teleoperation mode.
- Operator identity and motion authority are valid.
- A forward-motion request for 1.0 m/s is issued.
- Safety controller accepts the command.
- Motor controller reports non-zero output current.
- Wheel-encoder telemetry is absent because the encoder channel is degraded.
- No independent position change observation is present.

**Strongest defensible reconstruction**

A validly authorized motion command was accepted and motor output occurred. Physical displacement is not established because resulting-state observations are unavailable.

### S10 — Breaker command with contradictory consequence observation

**Domain:** electrical infrastructure  
**Primary traps:** consequence differs from intended result; contradiction.

**Facts**

- Protection logic determines that breaker B12 should open.
- Authority and safety predicates are satisfied.
- `OPEN B12` is issued and acknowledged by the controller.
- Controller state reports `OPEN` after 120 ms.
- An independent current transformer continues to measure load current above threshold for 1.8 seconds.
- The current transformer's calibration and health status are valid.
- A later field inspection finds a mechanical linkage fault.

**Strongest defensible reconstruction**

The controller accepted and reported an open state, but independent physical evidence contradicts immediate successful interruption. The later inspection supports a mechanical fault explanation.

### S11 — Trusted-looking timestamp with poor time quality

**Domain:** industrial incident reconstruction  
**Primary traps:** timestamp without established time quality; ordering uncertainty.

**Facts**

- Sensor A records pressure spike at `14:03:12.100Z`.
- Controller B records valve-close command at `14:03:12.080Z`.
- Both records are signed and internally intact.
- Sensor A clock uncertainty is ±20 ms.
- Controller B had lost synchronization 37 minutes earlier; observed drift bound is ±250 ms.
- No external witnessed time is available.

**Strongest defensible reconstruction**

Both events occurred near 14:03:12Z, but available time quality does not establish which occurred first. Signatures establish record integrity/attribution, not clock correctness.

### S12 — Stale retained checkpoint after authority revocation

**Domain:** autonomous/robotic authority  
**Primary traps:** cryptographically intact but stale evidence; identity/key validity versus current authority.

**Facts**

- Ranger signing key `K7` was valid at retained checkpoint C100.
- C100 is registry-signed and verifies.
- Authority history later revokes `K7` at C104.
- A verifier is presented C100 plus a Ranger record signed by `K7` after revocation.
- The presented C100 chain is internally valid but does not include C104.
- An independent retained authority head known to the verifier is C105.

**Strongest defensible reconstruction**

The presented checkpoint is cryptographically valid but stale relative to the verifier's retained authority state. `K7` cannot be treated as currently authorized for the later record based on C100.

## Trap-balance matrix

| Trap | Scenarios |
|---|---|
| intact but stale evidence | S04, S12 |
| identity established but authority invalid | S01, S12 |
| missing evidence does not prove event absence | S02, S08 |
| contradictory evidence | S06, S10 |
| shared upstream source | S03 |
| inference versus direct observation | S03, S05, S07 |
| command without execution proof | S06, S09 |
| execution/controller state without physical consequence proof | S09, S10 |
| observed consequence differs from intended result | S06, S10 |
| incomplete observation capability | S02, S08, S09 |
| timestamp without trusted time quality | S11 |
| valid historical record does not establish current standing | S01, S04, S12 |

## Fixed representation policy

For every scenario, create three neutral representation packages:

- **Condition A:** ordinary PROV representation using standard provenance constructs where applicable.
- **Condition B:** PROV plus domain extensions containing all substantive facts, but without Evidence Architecture's explicit bounded-verification semantics.
- **Condition C:** Evidence Architecture representation containing the same substantive facts with explicit verification dimensions, epistemic state, standing, source dependency, stage separation, contradictions, and nonclaims.

Condition C MUST NOT receive additional substantive evidence unavailable to A or B.

## Pre-execution review gate

Before evaluator recruitment:

1. prepare a fact-equivalence inventory for each scenario;
2. prepare A/B/C packages;
3. independently review each package for fact equivalence;
4. freeze exact artifacts and hashes;
5. freeze the scoring key and evaluator instructions;
6. determine applicable human-subject/IRB requirements.

**Execution status: NOT EXECUTED.**
