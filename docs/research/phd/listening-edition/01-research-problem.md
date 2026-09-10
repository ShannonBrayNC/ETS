# Part I — Why This Research Exists

Modern systems are extraordinarily good at producing records.

Cloud platforms generate audit logs. Applications emit events. Identity providers record authentication. Security tools preserve alerts. AI systems produce scores and tool calls. Industrial controllers report commands and state. Cameras sign media. Distributed systems calculate hashes, Merkle roots, signatures, attestations, and timestamps.

At first glance, this looks like an abundance of evidence.

But an abundance of records is not the same thing as an ability to reconstruct a consequential event without silently adding assumptions.

That gap is the research problem.

Consider a public-benefit approval. A reviewer authenticates with a valid credential. The approval record is digitally signed. The record's digest verifies. Those facts may establish that the record is intact and attributable under the stated trust model. But suppose the reviewer's delegated authority to approve claims above twenty-five thousand dollars expired two days earlier. The signature has not become mathematically invalid. The historical identity record has not become false. Yet the standing of the approval is materially different.

Or consider an automated cloud agent. Policy authorizes it to suspend an account. It sends a disable command. The target API returns “accepted.” Is the account disabled? Not necessarily. “Accepted for processing” is not the same proposition as “execution completed.” If a valid login succeeds ninety seconds later, the later event is not a footnote. It is contradictory evidence against the assumption that disablement had already taken effect.

Evidence Architecture begins by refusing to compress those distinctions.

## Data, records, provenance, evidence, verification, and proof

These terms are often used casually, but the research depends on separating them.

Data is the broadest category. A number from a sensor is data. A line in a log is data. A model output is data. A timestamp is data. Data may be useful, malformed, stale, incomplete, fabricated, or perfectly valid.

A record is data preserved as an account of an event, state, transaction, observation, or decision. Records add structure and persistence, but a record can still be wrong, misleading, incomplete, or outside the authority of its author.

Provenance describes origin, derivation, transformation, responsibility, or process history. Provenance can answer questions such as: what activity generated this artifact? What source did this model output depend on? Which agent was associated with this process? What earlier version did this record revise?

Provenance is powerful. It is also mature prior art. Evidence Architecture does not get to call provenance itself novel.

Evidence, in the research sense, is material offered to support or challenge a claim under an explicit trust and interpretation model. Evidence does not automatically become truth simply because it is signed, hashed, logged, or connected in a graph.

Verification is a procedure for checking a bounded proposition. A signature can be verified. A digest can be recomputed. Inclusion in a log can be verified against a root. A policy reference can be checked. A retained checkpoint can be compared for freshness. A consequence claim may be checked against a physical observation.

The important word is bounded.

Verification of one proposition must not silently imply another.

Proof is the strongest and most context-sensitive term. In mathematics, proof means a deductive demonstration from axioms or assumptions. In cryptography, a proof may establish a precise protocol relation. In law, “proof” is tied to legal standards and admissibility. In engineering, people often use “proof” casually to mean persuasive evidence.

The doctoral research therefore avoids using “proof” as a universal synonym for “verified record.” A Merkle inclusion proof can establish inclusion relative to a given tree root. It cannot prove that a physical event occurred, that a human had lawful authority, or that a source system captured every relevant event.

## The compression problem

Many real systems compress multiple questions into one status.

“Authenticated.”

“Verified.”

“Approved.”

“Completed.”

“Healthy.”

“No hazard detected.”

Those labels are useful operationally, but they can conceal distinct evidentiary dimensions.

A camera can authenticate a capture artifact while the scene itself remains staged.

A model can produce a signed fraud score while the underlying fraud remains unobserved.

Two models can produce two different scores while both depend on the same upstream source. Counting those as two independent confirmations would be a provenance error.

A policy document can remain cryptographically authentic after it becomes stale.

A controller can report a breaker as open while an independent current transformer still measures load current.

A sensor can report nothing because no event occurred, or because the sensor was offline. Those are not the same epistemic state.

This is why missing evidence is especially dangerous. Absence in a package can mean many things: the event did not happen, the event happened through an uncaptured channel, a connector failed, the source was unavailable, the expected artifact was never defined, or a malicious actor omitted it.

To infer event absence from evidence absence, the verifier needs an expectation or coverage basis.

The formal ETS work encodes this as a restrained rule: omission suspicion is valid relative to an external expected-event set. That is useful, but it does not magically prove that the expectation set itself is complete or authoritative.

## Independent reconstruction as the target

The overarching doctoral question asks whether a distributed system can produce evidence sufficient for an independent verifier to reconstruct and evaluate provenance, identity, authority, policy context, decision, action, and resulting state without simply trusting the originating system.

“Independent” does not mean omniscient.

An independent verifier can still be limited by bad sensors, incomplete capture, compromised keys, stale checkpoints, weak timing, hidden external channels, or missing policy records.

Independence instead means that the verifier should be able to inspect the evidence and its boundaries rather than rely on an undocumented assertion from the system that produced the event.

If the strongest defensible statement is “unknown,” then a good evidence architecture should preserve “unknown.”

If the strongest statement is “the command was accepted, execution unconfirmed,” then it should not collapse that into “completed.”

If the strongest statement is “this record is authentic but stale,” then authenticity should not be upgraded into current standing.

That is the research motivation in one sentence:

The problem is not that modern systems have too little telemetry. The problem is that telemetry, provenance, integrity, authority, execution, consequence, and truth are too often collapsed into claims that are stronger than the evidence actually supports.

Evidence Architecture investigates whether a disciplined representation can prevent that collapse.

---

## Reference notes — do not narrate

Primary support:
- `docs/research/phd/RESEARCH_QUESTIONS.md`
- `docs/research/phd/METHODOLOGY_AND_RESEARCH_INTEGRITY.md`
- `docs/research/phd/EXP-001_PREREGISTRATION.md`
- `docs/research/phd/EXP-001_SCENARIO_CORPUS.md`
- `docs/research/FORMAL_MODEL_CLAIMS.md`
- `docs/research/FORMAL_THEOREMS.md`
