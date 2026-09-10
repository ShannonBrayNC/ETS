# ElevenLabs Production Notes

## Purpose

These notes describe how to turn the doctoral listening edition into natural speech without changing the scientific meaning.

The manuscript is designed for comprehension by ear, not literal recitation of repository syntax.

## Preferred reading source

Use `FULL_LISTENING_EDITION.md` for one continuous production, or render the chapter files separately for easier correction and chapter navigation.

Do **not** speak any section headed `Reference notes — do not narrate`.

Do not speak repository paths, commit SHAs, Git blob IDs, raw SHA-256 digest strings, Markdown table separators, code fences, or source-control metadata unless a specific technical appendix recording is intentionally being produced.

The exact identifiers remain in the written reference material for auditability.

## Pronunciation guidance

| Term | Recommended speech |
|---|---|
| ETS | “E T S” |
| Evidence Transparency System | say in full on first formal-methods reference where useful |
| Evidence Architecture | say in full |
| EA-C001 | “E A C zero zero one” |
| EA-C002 | “E A C zero zero two” |
| EXP-001 | “experiment zero zero one” after first introduction |
| W3C | “W three C” |
| W3C PROV | “W three C Prov” |
| PROV-O | “Prov O” |
| IETF | “I E T F” |
| RATS | “rats” |
| in-toto | “in TOH-toh” |
| SHA-256 | “S H A two fifty-six” |
| Merkle | “MER-kul” |
| TLA+ | “T L A plus” |
| Alloy | ordinary English “alloy” |
| Beta-Bernoulli | “BAY-tuh ber-NOO-lee” |
| provenance | “PROV-uh-nuhns” |
| epistemic | “ep-ih-STEM-ik” |
| cyber-physical | “cyber physical” |
| IRB | “I R B” |
| HTTP 202 Accepted | “H T T P two-oh-two, accepted,” or simply “accepted for processing” |
| UTC | “U T C” |
| K7 | “K seven” |
| C100 / C104 / C105 | “C one hundred,” “C one-oh-four,” “C one-oh-five” |
| R17 / U9 | “R seventeen,” “U nine” |

For PROV, keep the same pronunciation throughout. Avoid spelling P-R-O-V unless an acronym-heavy technical recording requires it.

## Equations and technical notation

Prefer the spoken explanation already embedded in the manuscript.

Where the assignment equation appears, do not read punctuation. Say:

“For evaluator index e and scenario index s, add the two indexes and take the remainder after division by three.”

Where evidence age is relevant, say:

“Evidence age is decision time minus observation time.”

Do not read hexadecimal hashes aloud.

Do not read JSON syntax aloud.

Do not read arrows as punctuation. Convert a chain such as `decision -> requested action -> accepted action -> controller output -> physical response -> observed result` into natural speech: “decision, then requested action, then accepted action, then controller output, then physical response, and finally observed result.”

## Intentional pauses

Use a short pause, roughly a half second, after major claim-boundary contrasts, especially:

“Observed is not the same as authenticated.”

“Authenticated is not the same as authorized.”

“Authorized is not the same as executed.”

“Executed is not necessarily the same as consequential.”

“A recorded consequence is not automatically independently verified truth.”

Use a slightly longer pause, roughly one second, before and after “no standing, no bind,” and before the final research question in the closing lecture.

For the twelve scenarios, insert a clear chapter-style pause between scenarios so they do not blend together.

## Emphasis

Use restrained emphasis. This is a doctoral listening edition, not a promotional voice-over.

Emphasize negation where scientific boundaries depend on it:

- “has **not** been executed”;
- “does **not** establish truth”;
- “is **not** independent certification”;
- “does **not** prove physical consequence”;
- “remains **candidate**.”

Avoid dramatic emphasis that makes a hypothesis sound like a result.

## Section breaks

Recommended production hierarchy:

- major Part heading: 1.5 to 2 second pause;
- chapter heading: about 1 second;
- subsection transition: 0.5 to 0.8 second;
- scenario change: about 1 second.

If ElevenLabs supports chapter-level projects, render each numbered Markdown file as a separate chapter, then order Part VIII (`11-next-steps.md`) before Part IX (`10-doctoral-significance.md`) as documented in the README.

## Material that should remain written only

Keep the following out of ordinary spoken production:

- source paths;
- exact commit and blob identifiers;
- exact randomization seed;
- full assignment matrices and scenario-order permutations;
- individual packet hashes;
- historical and authoritative hash JSON contents;
- traceability-matrix tables;
- code implementation excerpts;
- Markdown status metadata.

Narrate the meaning of those controls instead.

Say “the randomization seed was frozen before outcome data existed,” not the seed itself.

Say “both clean render passes produced the same thirty-six packet hashes,” not thirty-six digest values.

## Tables

Tables in canonical source material have been translated into prose in the listening chapters. If future source additions include tables, narrate them as comparisons or grouped findings. Do not read row and column delimiters.

## Handling citations and prior-art names

Read the names of major prior-art families because they are conceptually important. Do not read full URLs or DOI strings.

The traceability matrix and canonical WP1 documents remain the exact written source record.

## Voice and pacing recommendation

Use an analytical, measured voice. Aim for a pace slower than a news read and faster than a ceremonial speech. Technical contrasts need enough space to be heard as different propositions.

Avoid a sales cadence.

For dense sections—prior art, measurement, and human-subjects review—slightly reduce pace. For the scenario chapter, allow more narrative movement because concrete examples carry the concepts.

## Scientific-status safeguard

Before final audio export, search the spoken script for status-inflating phrases such as claims that EXP-001 already produced findings, that the experiment proved the theory, that independent reviewers have certified the scenarios, that institutional approval exists, or that EA-C001 or EA-C002 has already been established as novel.

Those claims should not appear unless future canonical evidence changes the status and the listening edition is deliberately regenerated from that later source state.

At the source baseline for this edition:

- EXP-001 is NOT EXECUTED;
- independent fact-equivalence certification is incomplete;
- institutional determination is absent;
- EA-C001 and EA-C002 remain candidate contributions.
