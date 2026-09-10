# Part V — The Twelve EXP-001 Scenarios

The twelve scenarios are controlled teaching cases designed to expose recurring reconstruction errors across three domains: digital and administrative systems, AI and automated systems, and cyber-physical systems. Each scenario contains at least two preregistered traps. The word “trap” means a place where a common but unsupported inference is possible.

## Scenario One — expired delegated authority

A public-benefit reviewer authenticates with a valid agency credential and holds the directory role of Senior Reviewer. The reviewer approves a claim for thirty-one thousand five hundred dollars. The approval record is signed and its digest verifies.

But the specific delegation that allowed this reviewer to approve claims above twenty-five thousand dollars expired two days before the approval. No replacement delegation appears in the evidence package. A downstream payment instruction is generated, but there is no settlement confirmation.

The evidence supports the identity, role, signed approval record, expired supplied delegation, and generated payment instruction. It does not prove that some other lawful authority could not have existed outside the package. It does not establish substantive applicant eligibility. It does not establish payment settlement.

This scenario separates identity from standing and instruction from consequence.

## Scenario Two — missing finance approval

A procurement policy requires both Procurement and Finance approval for purchases over one hundred thousand dollars. A purchase order for one hundred forty-eight thousand dollars is issued. Procurement approval is present. Finance approval is absent from the package.

The capture system, however, reports only ninety-two percent ingestion availability during the relevant interval because one connector was degraded. The vendor accepted the purchase order. No evidence establishes whether Finance approved through another channel.

The supported statement is: Finance approval is absent from this package. The unsupported overstatement is: Finance approval did not occur.

This is the difference between missing evidence and evidence of absence.

## Scenario Three — two analytical scores from one source

One source record contains an address mismatch. Model M1 consumes that source and produces a risk score of zero point eight two. Model M2 consumes the same source and produces a risk score of zero point seven nine. M2 also consumes a derived field, but that field ultimately comes from the same source. Both outputs are signed by their service identities.

An analyst describes the result as two independent systems confirming the risk.

There are two model outputs, but the material dependency is shared. The outputs support two elevated inferences. They do not provide two independent corroborations, and neither score is direct observation of the underlying real-world condition.

This scenario teaches source dependence, inference lineage, and false corroboration.

## Scenario Four — authentic but stale policy

Policy version four is signed by an authorized publisher and its signature and digest verify. Later, version five supersedes it. After that supersession, an external recipient retrieves version four from a valid archival endpoint.

The archival receipt proves the bytes and publisher signature for version four. It does not establish that version four remained operative on the later date.

A record can remain perfectly authentic while losing current standing. Staleness does not corrupt the past. It changes what the past artifact can support about the present.

## Scenario Five — AI recommendation versus human decision

An AI lending model produces a recommendation to deny an application. The model version and runtime identity are recorded. Policy requires a human underwriter to authorize this class of denial.

The human underwriter authenticates, has active authority, reviews the recommendation, and approves the denial. A denial notice is generated. No evidence proves delivery to the applicant.

The model produced a recommendation. The authorized human made the decision. A notice was generated. Delivery remains unverified. The AI recommendation remains an inference rather than direct proof of the applicant's objective condition.

Model output and human decision are related without being the same event.

## Scenario Six — action accepted, execution unconfirmed

An AI operations agent identifies an account as high risk. Policy authorizes suspension. The agent sends a disable-account request. The identity service returns an HTTP “202 Accepted” response with an operation identifier. No completion event appears. Ninety seconds later, a valid authentication attempt succeeds.

The strongest conclusion is not that the account was successfully disabled. The request was authorized and accepted for processing. Successful execution is not established. The later successful authentication contradicts the assumption that disablement had already taken effect.

A service can tell you what it accepted. A later operational event may be necessary to establish whether the intended state actually formed.

## Scenario Seven — authentic capture versus scene truth

A camera signs a media artifact using a registered device key. The bytes match the signed digest. An AI synthetic-media detector assigns a score of zero point nine one for likely synthetic content. The detector version and threshold are known. There is no independent source artifact proving whether the content was staged, generated, or post-processed.

The camera signature supports cryptographic linkage to the registered capture device under the stated trust model. The detector supports a strong model inference about synthetic-media likelihood. Neither mechanism proves scene truth.

A genuine device can capture a staged scene. A detector can be wrong. A signed file can be authentic as a captured artifact while a semantic claim about the scene remains unsupported.

## Scenario Eight — unavailable sensor coverage

A safety-monitoring model receives feeds from sensors A, B, and C. Sensor C has been offline for eleven minutes and its health record marks it unavailable. Sensors A and B show no hazard indications. The model outputs “no hazard detected.”

But sensor C is the only sensor capable of observing the east enclosure. There is no independent east-enclosure observation.

The strongest conclusion is coverage-bounded. No hazard was detected in the regions observed by A and B. The east enclosure was unobservable. Therefore “no hazard existed anywhere” exceeds the evidence.

Capability state is itself evidentiary context. Knowing what the system could not observe is necessary to interpret what it did not detect.

## Scenario Nine — Ranger motion request versus physical displacement

Ranger is operating in teleoperation mode. The operator identity and motion authority are valid. A request is issued for forward motion at one meter per second. The safety controller accepts the request. The motor controller reports nonzero output current.

But the wheel-encoder channel is degraded and there is no independent position-change observation.

The evidence supports an authorized request, controller acceptance, and motor output. It does not establish physical displacement. The vehicle might be obstructed, experience wheel slip, or have a drivetrain fault. The package simply does not establish the resulting position.

This is action-result non-collapse in physical form.

## Scenario Ten — breaker request versus observed consequence

Protection logic determines that breaker B12 should open. Authority and safety predicates are satisfied. The controller accepts the open request and reports its state as open.

An independent current transformer, whose calibration and health are valid, continues to measure load current above threshold for one point eight seconds. Later field inspection finds a mechanical linkage fault.

The action request and controller-state transition are supported. Immediate successful physical interruption is contradicted by the current measurement. The later inspection supports the mechanical-fault explanation.

This scenario shows why an independent consequence observation can materially change reconstruction.

## Scenario Eleven — uncertain clocks

Sensor A records a pressure spike at fourteen hours, three minutes, twelve point one zero zero seconds UTC. Controller B records a valve-close action twenty milliseconds earlier by its own timestamp. Both records are signed and internally intact.

If timestamps were perfect, the controller event would appear to come first. But Sensor A has a twenty-millisecond uncertainty, while Controller B lost synchronization thirty-seven minutes earlier and has possible drift of plus or minus two hundred fifty milliseconds. No independent witnessed time exists.

Both events occurred near the stated time, but the available time quality does not establish their order. A signature protects the record. It does not repair the clock.

This scenario prevents temporal precision from being inferred merely because a timestamp looks precise.

## Scenario Twelve — stale authority checkpoint

Ranger key K7 is valid at authority checkpoint C100. That checkpoint is registry-signed and cryptographically valid. Later, at checkpoint C104, K7 is revoked. A verifier is then shown C100 together with a later Ranger record signed by K7.

The presented checkpoint is authentic, but the verifier independently retains authority state through C105. The older checkpoint is stale. The fact that C100 is valid does not make K7 currently authorized.

This scenario combines freshness, retained state, revocation, and standing.

## The common lesson

Across all twelve scenarios, the research repeatedly asks the evaluator to resist one form of collapse:

Identity into authority.

Authenticity into currentness.

Absence into nonoccurrence.

Multiplicity into independence.

Inference into observation.

Recommendation into decision.

Acceptance into execution.

Controller state into physical consequence.

Timestamp precision into time accuracy.

Historical validity into present standing.

The experiment does not assume Evidence Architecture is the only way to prevent those errors. Condition B, the domain-extended provenance comparator, is specifically allowed to encode the same facts with rich domain labels.

If evaluators can reconstruct the scenarios equally well from that representation, the Evidence Architecture-specific claim becomes smaller.

The scenarios are therefore both a tutorial in the theory and a test of whether the theory adds measurable value.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/EXP-001_SCENARIO_CORPUS.md`
- `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/ranger/cyber-physical-observability.md`
