# Source-to-Listening-Edition Traceability Matrix

**Listening-edition baseline:** `main` at `374c0ab32cd1ba0ffda1b75fa561fc075a60fd11`

This matrix identifies which repository artifacts materially support each listening chapter. It also records status distinctions needed to avoid treating historical or superseded artifacts as current.

| Source artifact | Current role / status at baseline | Listening edition use |
|---|---|---|
| `docs/research/phd/README.md` | Doctoral qualification framework; conservative research portfolio rules | `00`, `10`, `11` |
| `docs/research/phd/RESEARCH_QUESTIONS.md` | Canonical RQ0-RQ8 and hypotheses; questions are not answered merely by tests | `00`, `01`, `02`, `10`, `12` |
| `docs/research/phd/CONTRIBUTION_LEDGER.md` | EA-C001/EA-C002 and other contributions remain candidate unless promoted by evidence | `00`, `02`, `03`, `04`, `10`, `12` |
| `docs/research/phd/EXPERIMENT_LEDGER.md` | Experiment classification and EXP-001 prospective record; some packet-status wording predates later freeze-resolution artifacts | `00`, `04`, `05`, `08`, `10`, `11`, `12` |
| `docs/research/phd/METHODOLOGY_AND_RESEARCH_INTEGRITY.md` | Prospective/retrospective distinction, claim discipline, negative-result and reproducibility rules | `00`, `01`, `07`, `08`, `10`, `11`, `12` |
| `docs/research/phd/WP1_EVIDENCE_OBJECT_GRAPH_PRIOR_ART.md` | First-pass prior-art qualification; broad object/graph novelty excluded | `02`, `03`, `04` |
| `docs/research/phd/WP1_PROV_RELATION_MAPPING_AND_DEEPER_PRIOR_ART.md` | Relation-by-relation W3C PROV mapping and narrowed candidate semantics | `02`, `03`, `04`, `05` |
| `docs/research/phd/WP1_DEEP_LITERATURE_QUALIFICATION.md` | Deeper literature qualification: semirings, workflow, authorization, claim graphs, AI/ML, CPS/runtime assurance | `03`, `04`, `05`, `10` |
| `docs/research/phd/EXP-001_PREREGISTRATION.md` | Frozen prospective experiment; execution status NOT EXECUTED | `00`, `01`, `04`, `05`, `06`, `07`, `08`, `09`, `11`, `12` |
| `docs/research/phd/EXP-001_SCENARIO_CORPUS.md` | Frozen 12-scenario corpus; NOT EXECUTED | `01`, `05`, `06`, `07` |
| `docs/research/phd/EXP-001_CONDITION_PACKAGES.md` | Frozen A/B/C rendering contract and fact-equivalence requirement | `05`, `06`, `09` |
| `docs/research/phd/EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md` | Frozen fact inventory, claim labels, error taxonomy, metric formulas | `05`, `06`, `07`, `09`, `11` |
| `docs/research/phd/EXP-001_EVALUATOR_INSTRUCTIONS.md` | Frozen neutral evaluator instructions and six questions | `05`, `07`, `09` |
| `docs/research/phd/EXP-001_ASSIGNMENT_AND_RANDOMIZATION.md` | Frozen design procedure; older “no seed instantiated” status text is superseded by later freeze files | `05` |
| `docs/research/phd/EXP-001_ASSIGNMENT_FREEZE.md` | Current frozen seed, opaque mapping, 12 prospective slots, scenario orders; no outcome data | `05`, `11` |
| `docs/research/phd/EXP-001_ASSIGNMENT_MATRIX.md` | Current frozen balanced matrix and cyclic assignment rule | `05`, `11` |
| `docs/research/phd/EXP-001_PACKET_GENERATION_STATUS.md` | Historical intermediate status saying generation in progress; superseded by packet freeze resolution and artifact manifest | `08` historical-status example only |
| `docs/research/phd/WP2_PACKET_FREEZE_RECONCILIATION.md` | Historical prospective reconciliation plan after failed expected manifest; later completed by resolution artifact | `05`, `08` |
| `docs/research/phd/exp001-packets/PACKET_FREEZE_DISCREPANCY.md` | Historical failed first freeze; preserved integrity record; not current authoritative packet state | `05`, `08`, `09` |
| `docs/research/phd/EXP-001_PACKET_FREEZE_RESOLUTION.md` | Current deterministic two-pass rendering resolution: 36 + 36 matching hash sets; NOT EXECUTED | `05`, `08`, `09`, `11` |
| `docs/research/phd/EXP-001_ARTIFACT_MANIFEST.md` | Most complete current pre-execution status record: internal deterministic freeze substantially complete, external gates pending, NOT READY FOR CONFIRMATORY EXECUTION | `00`, `05`, `08`, `09`, `11`, `12` |
| `docs/research/phd/exp001-packets/packet_source.json` | Frozen packet source | `05` control explanation |
| `docs/research/phd/exp001-packets/generate_packets.py` | Frozen deterministic renderer | `05`, `08` control explanation |
| `docs/research/phd/exp001-packets/rendered_sha256.expected.json` | Historical expected manifest retained after failed first freeze; not authoritative for packet use | `05`, `08` |
| `docs/research/phd/exp001-packets/rendered_sha256.authoritative.json` | Current authoritative packet hash manifest after successful two-pass regeneration | `05`, `08` |
| `docs/research/phd/exp001-packets/assignment_matrix.authoritative.json` | Frozen machine-readable assignment matrix | `05` |
| `docs/research/phd/exp001-packets/scenario_order.authoritative.json` | Frozen machine-readable scenario orders | `05` |
| `docs/research/phd/exp001-packets/rendered/` | 36 materialized evaluator packets; byte-frozen but not independently fact-equivalence-certified | `05`, `09` |
| `docs/research/phd/EXP-001_EQUIVALENCE_CERTIFICATION.md` | Required pre-execution independent gate; no scenario independently certified yet | `05`, `09`, `11` |
| `docs/research/phd/EXP-001_INDEPENDENT_REVIEWER_HANDOFF.md` | Reviewer-ready procedure; explicitly not a certification result | `09`, `11` |
| `docs/research/phd/exp001-equivalence/README.md` | Review scaffolding; no independent certification | `09`, `11` |
| `docs/research/phd/exp001-equivalence/generate_certification_forms.py` | Tool to materialize blank certification forms; not a completed review | `09` |
| `docs/research/phd/EXP-001_ANALYSIS_SKELETON.md` | Frozen pre-data analysis structure; no outcome data | `07`, `08`, `11` |
| `docs/research/phd/exp001-analysis/README.md` | Descriptive-analysis implementation boundary; no participant data | `07`, `08`, `11` |
| `docs/research/phd/exp001-analysis/exp001_analysis.py` | Executable descriptive analysis; source-level denominator alignment issue noted prospectively in listening edition | `07`, `08`, `11` |
| `docs/research/phd/EXP-001_HUMAN_SUBJECTS_DECISION_MEMO.md` | Pre-recruitment decision support; not an institutional determination; recruitment blocked | `09`, `11` |
| `docs/research/phd/EXP-001_INSTITUTIONAL_REVIEW_PACKET.md` | Submission-ready draft; no determination or approval | `09`, `11` |
| `docs/research/phd/EXP-001_INSTITUTIONAL_SUBMISSION_COVER_MEMO.md` | Draft request for written institutional determination | `09`, `11` |
| `docs/research/phd/EXP-001_PARTICIPANT_INFORMATION_DRAFT.md` | Draft only; not approved for recruitment | `09`, `11` |
| `docs/research/phd/DOCTORAL_READINESS_MATRIX.md` | Program/route planning snapshot. Its older “literature review missing” row predates later WP1 work, so later WP1 artifacts govern current literature progress | `10`, `11` |
| `docs/research/phd/PUBLIC_WORKS_MANIFEST.md` | Candidate public-works inventory; inclusion does not imply university acceptance or peer review | `10` |
| `docs/architecture/EVIDENCE_STANDING_CONSEQUENCE_CUSTODY.md` | Normative architecture boundary for Reconstruction, Standing, and Consequence Custody; consequence custody only for implementations that actually enforce it | `02`, `10`, `12` |
| `docs/research/ranger/cyber-physical-observability.md` | Research contract for capability state, measurement quality, epistemic ceiling, action/result non-collapse, and cyber-physical result evidence | `02`, `06`, `10`, `12` |
| `ets/evidence_object/models_v2.py` | Implemented Evidence Object v2 envelope and canonical identity boundary; engineering evidence, not novelty evidence | `02`, `04`, `10` |
| `docs/research/FORMAL_MODEL_CLAIMS.md` | Formal claim map and explicit non-goals | `00`, `08`, `10` |
| `docs/research/FORMAL_TRACEABILITY_MATRIX.md` | Conservative mapping among formal models, code, tests, and status classes | `00`, `08`, `10` |
| `docs/research/FORMAL_THEOREMS.md` | Implementation-facing theorem obligations and limitations; not blanket mathematical publication claims | `01`, `08`, `10` |
| `docs/research/REPRODUCIBILITY_APPENDIX.md` | Internal reproduction procedures and formal-checking caveats | `08`, `10` |

## Chapter-to-source summary

| Listening chapter | Primary canonical support |
|---|---|
| `00-introduction.md` | doctoral README, research questions, ledgers, integrity framework, formal claim controls |
| `01-research-problem.md` | research questions, integrity rules, scenario corpus, formal omission/nonclaim rules |
| `02-evidence-architecture-thesis.md` | contribution ledger, PROV mapping, standing/consequence architecture, Ranger observability, Evidence Object implementation |
| `03-prior-art.md` | all three WP1 prior-art qualification artifacts |
| `04-candidate-contributions.md` | contribution ledger plus WP1 narrowing/falsification work |
| `05-exp001-design.md` | preregistration, condition contract, equivalence controls, assignment/freeze artifacts, packet discrepancy/resolution/manifest |
| `06-exp001-scenarios.md` | frozen scenario corpus and scoring key |
| `07-measurement-and-analysis.md` | preregistration, scoring key, analysis skeleton, analysis implementation |
| `08-research-integrity.md` | integrity framework, discrepancy/resolution history, formal/nonclaim and reproducibility controls |
| `09-independent-review-and-human-subjects.md` | equivalence certification/handoff, human-subjects memo, institutional packet, cover memo, participant draft |
| `10-doctoral-significance.md` | readiness matrix, public works, ledgers, formal/reproducibility artifacts, Ranger program |
| `11-next-steps.md` | current artifact manifest and all external/pre-execution gate artifacts |
| `12-closing-lecture.md` | research questions, ledgers, current manifest, standing/consequence and Ranger architecture |

## Traceability caveat

This matrix documents the basis of the derivative narration. It does not amend the source artifacts. Where a source contains a historically correct but now superseded status line, the listening edition uses the later status-bearing artifact and describes the earlier file only where its history matters.
