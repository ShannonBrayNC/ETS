# VRX Physics Laboratory — Book Edition

This directory is the **authoritative narration-safe book edition** of the VRX Physics Laboratory curriculum.

The original files in `../episodes/` remain the research/engineering lecture notes. They preserve denser equations, experiment references, and phase-review context. The files in `book/chapters/` are rewritten specifically for spoken delivery so ElevenReader does not have to carry the teaching burden by reading formulas aloud without explanation.

## Book purpose

The book connects three intellectual layers:

1. **Traditional physics of evidence** — physical events leave measurable traces, and physics helps reconstruct what happened.
2. **Instrumented cyber-physical systems** — machines can preserve physical observations while events occur rather than relying only on traces discovered afterward.
3. **Evidence Architecture** — observations, calibration, timing, models, authority, consequences, provenance, and integrity are retained so an independent party can evaluate the claim later.

The central book proposition is:

> **A machine assertion is not the same thing as an independently supported physical claim.**

## Production order

For a single ElevenReader manuscript, concatenate the files in exactly this order:

1. `front-matter.md`
2. `chapters/01-how-do-we-know-anything-happened.md`
3. `chapters/02-why-does-vrx-move.md`
4. `chapters/03-motion-has-a-history.md`
5. `chapters/04-where-did-the-energy-go.md`
6. `chapters/05-the-physics-of-stopping.md`
7. `chapters/06-electricity-before-magnetism.md`
8. `chapters/07-turning-current-into-force.md`
9. `chapters/08-build-the-vrx-force-map.md`
10. `chapters/09-why-current-doesnt-change-instantly.md`
11. `chapters/10-heat-remembers-what-electricity-did.md`
12. `chapters/11-why-machines-shake.md`
13. `chapters/12-can-we-prove-what-happened.md`

`technical-review.md` is editorial/reviewer material and is **not** part of the narrated manuscript.

## Spoken-math production rule

Every important equation in the book edition follows this pattern:

1. explain the physical idea in ordinary language;
2. state the relevant measurement or boundary;
3. introduce the equation;
4. read it aloud in words;
5. define the variables and units;
6. state the assumptions/domain;
7. provide a physical or numerical example when useful;
8. explain what claim the equation can and cannot support.

The printed equation is a compact reference. It is never the sole explanation.

## Technical corrections incorporated in the book edition

The book edition contains several refinements identified during the full twelve-module technical review:

- uncertainty-interval overlap is not treated as a standalone significance test;
- `F = ma` is explicitly net external force, not automatically actuator force;
- energy ledgers require non-overlapping accounting terms and a declared system boundary;
- impulse comparisons preserve sign, rebound, sampling, bandwidth, and possible parallel force paths;
- `V = IR` and `V²/R` are bounded to the appropriate ohmic element/condition;
- electromechanical force is explained through magnetic co-energy and the sign/domain of `1/2 I² dL/dx`;
- force-map predictions distinguish measured points, interpolation, uncertainty, and out-of-domain rejection;
- inductive voltage uses the more general `v = Ri + dλ/dt`, including the motion-dependent term when `λ = L(x)i`;
- thermal terminology distinguishes internal-energy generation from heat transfer;
- vibration analysis distinguishes a descriptive spectral acceleration ratio from a defensible frequency-response estimate;
- logarithmic decrement uses same-sign peaks separated by one full cycle for the standard adjacent-cycle form;
- coherence is treated as a diagnostic rather than a probability of truth or proof of causation;
- Chapter 12 introduces explicit `INCONCLUSIVE` / `INSUFFICIENT_EVIDENCE` outcomes.

## Safety boundary

The book remains strictly within the low-voltage, current-limited, enclosed, mechanically captive VRX-R0 laboratory configuration. It does not require free-launching projectiles, destructive impacts, suppression defeat, deliberate high-voltage spike generation, maximum-force searches, or thermal-limit searches.

## Review artifact

See `technical-review.md` for the chapter-by-chapter physics and mathematics review that drove this edition.