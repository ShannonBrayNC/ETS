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

## Canonical source and generated editions

`book-manifest.json` defines the canonical source order. Hand editing is permitted only in the canonical files listed by that manifest:

- `front-matter.md`
- `chapters/*.md`
- `back-matter/glossary.md`
- `back-matter/references-and-further-reading.md`
- `technical-review.md` for the research appendix

The files under `publication/` are generated artifacts and must not be edited by hand.

`tools/build_publication.py` creates two outputs from the same canonical source:

- `publication/VRX_Physics_Laboratory_ElevenReader.md`
- `publication/VRX_Physics_Laboratory_Research_Edition.md`

The ElevenReader build removes display-only LaTeX after the concept has already been explained in narration, removes raw URLs and low-value Markdown syntax, converts common mathematical symbols into spoken words, normalizes tables and headings, and keeps the book/chapter structure visibly bold for rich-text import.

The research edition preserves equations, technical Markdown, glossary, references, and the technical-review appendix.

The dedicated `vrx-physics-publication.yml` workflow rebuilds and commits both generated files whenever canonical source changes on the publication branch. Generated-file commits do not retrigger the workflow.

To build locally:

```bash
python docs/research/ranger/vrx-physics/book/tools/build_publication.py
python docs/research/ranger/vrx-physics/book/tools/build_publication.py --check
```

## Production order

The canonical order is:

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
14. `back-matter/glossary.md`
15. `back-matter/references-and-further-reading.md`

`technical-review.md` is appended only to the generated research edition.

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

## Narration pacing rules

For ElevenReader production:

- title and chapter headings remain bold and are separated by blank lines;
- deep Markdown heading syntax is converted to simple spoken section headings;
- display equations are omitted only from the audio-oriented generated edition because their physical meaning has already been narrated;
- speaker labels remain intact so the Instructor, Investigator, and Independent Verifier structure is understandable;
- raw URLs are omitted from narration and retained in the research edition;
- tables become semicolon-delimited spoken rows rather than pipe-delimited Markdown;
- symbolic arrows and common mathematical symbols are converted into words;
- pauses are created with paragraph spacing rather than artificial stage directions;
- no generated audio manuscript should be edited independently of canonical source.

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
