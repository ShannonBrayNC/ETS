# Approved Microsoft alignment execution priority

Approved by Shannon Bray on November 7, 2026. This decision promotes all 14 technical review findings into the next execution priority. Approval authorizes planning and development; it does not establish live qualification.

## Order of execution

| Gate | Work and dependencies | Exit evidence |
|---|---|---|
| Current demonstration | CE #637: OBS-01 then OBS-02; OBS-03 profile supports ingestion | Pinned Distro, privacy negatives, retained real Microsoft ingestion and complete correlation |
| Pilot week 1 / #957 Sprint 4 | ID-01, OBS-03, VER-01 design; scope and access freeze | Identity/runtime/trust matrix; supported signing profile; access and staffing confirmed |
| Pilot week 2 | DSC-01, M365-01, TCM-01 | Repeated read-only drift, revoked access and stale-checker unknown; verified prebaseline archive |
| Pilot week 3 / #957 Sprint 5 | VER-01 offline fixture | Actual payload-byte checks, offline trust and tamper negatives; fixture is not complete live Q5 |
| Pilot week 4 | QRF read-only investigation; ID-01 and EXEC-01 security tests | Exception lookup, bounded proposal and denied investigator writes |
| Pilot week 5 / security gate | EXEC-01 after identity, verifier and source gates | One authorized disposable repair; conflict, expiry, retry, rollback and independent read-back evidence |
| Pilot week 6 / #957 Sprints 7–8 decisions | QUAL-01 after all required technical gates | Actual repair bundle, independent reviewer output, limitations and go/no-go; partnership remains conditional |
| Follow-on migration | MIG-01 | Legacy MOF/assignment equivalence before September 30, 2027 retirement |

Six working weeks is an execution estimate contingent on staffing, access and gate outcomes, not six additional sprints or a promised November completion. #957 Sprint 6 security controls move before the first live write. The existing governed SharePoint demonstration remains the first commercial Agent 365 scenario. Reuse qualified components; do not create a competing demo path.

## Approved backlog

- [ ] [PLAN-01 — Reconcile Agent 365 execution gates and dependency map](https://github.com/ShannonBrayNC/ETS/issues/959) (P0)
- [ ] [OBS-01 — Migrate Minesweeper observability to pinned Microsoft OpenTelemetry Distro](https://github.com/ShannonBrayNC/EchoMedia-ContentEngine/issues/1211) (P0)
- [ ] [OBS-02 — Gate tenant qualification on real ingestion and complete correlation](https://github.com/ShannonBrayNC/EchoMedia-ContentEngine/issues/1212) (P0)
- [ ] [ID-01 — Qualify read-only investigator and separately authorized execution identities](https://github.com/ShannonBrayNC/ETS/issues/960) (P0)
- [ ] [OBS-03 — Freeze Agent 365 telemetry semantics and evidence custody profile](https://github.com/ShannonBrayNC/ETS/issues/961) (P1)
- [ ] [DSC-01 — Qualify scheduled DSC 3 read/test runner and freshness failures](https://github.com/ShannonBrayNC/ETS/issues/962) (P0)
- [ ] [M365-01 — Qualify selected read-only Microsoft365DSC resource and runtime](https://github.com/ShannonBrayNC/ETS/issues/963) (P1)
- [ ] [TCM-01 — Block baseline replacement until configuration monitor archive verifies](https://github.com/ShannonBrayNC/ETS/issues/964) (P1)
- [ ] [VER-01 — Qualify configuration evidence profile using existing ETS signing profiles](https://github.com/ShannonBrayNC/ETS/issues/965) (P0)
- [ ] [EXEC-01 — Enforce approval-bound disposable executor and independent read-back](https://github.com/ShannonBrayNC/ETS/issues/966) (P0)
- [ ] [QUAL-01 — Qualify real repair bundle with second engineer and offline tamper tests](https://github.com/ShannonBrayNC/ETS/issues/967) (P0)
- [ ] [MIG-01 — Build legacy MOF to Machine Configuration equivalence acceptance suite](https://github.com/ShannonBrayNC/ETS/issues/968) (P1)

## Dependency rules

OBS-02 depends on OBS-01 and the OBS-03 semantic profile. Live collection depends on ID-01 and each source's qualified runtime. EXEC-01 live execution depends on ID-01, VER-01 and the selected source's baseline/before-state gates; TCM baseline replacement also depends on TCM-01 archival verification. QUAL-01 depends on the complete selected live case including execution and independent read-back. MIG-01 is follow-on, not a pilot prerequisite.

PLAN-01 is coordination; ETS #828 remains the Q0–Q5 qualification authority and must remain open until its evidence gates pass. #957 owns the post-demo commercial sequence; CE #637 owns current demo completion. No issue closes solely because this plan was approved.

## Technical decisions and scope

- Findings F01/F03 → OBS-01; F02 → OBS-02; F04/F05 → VER-01; F06 → ID-01; F07 → OBS-03; F08 → DSC-01; F09 → M365-01; F10 → TCM-01; F11 → MIG-01; F12 → EXEC-01; F13 → PLAN-01; F14 → QUAL-01.
- Use existing supported ETS Ed25519/proof profiles. CMS is not a pilot requirement. Preserve historical proof semantics; any new configuration verdict profile is explicitly versioned.
- A successful proof signature is not validation of separately exported artifact bytes, authorization or repair. Qualify each verdict and report uncertainty separately.
- Microsoft telemetry ingestion and ETS evidence custody are separate observations. Do not use SDK loader success, export attempt or synthetic traces as live ingestion proof.
- Standalone DSC 3 requires an owned trigger and freshness policy. Machine Configuration assignment evaluation and legacy LCM behavior are qualified separately.
- Work IQ supplies authorized business context, not automatic write authority. Qualify delegated enterprise MCP and any autonomous broker separately.
- QRF's later-November beta is a read-only thin slice. WatchTower architecture/synthetic fixtures do not establish a production sensor. Full repair qualification follows measured evidence.
- Edge and Mobile retain concurrent P0 qualification lanes. Physical/Ranger gates and protected active baselines remain intact. No blanket Distro/DSC dependency is imposed on every ETS product.

## Change control and completion

The reviewed alignment work takes precedence over discretionary expansion and conditional partnership work. Human assignees and calendar commitments remain unset until staffing is confirmed; accountable engineering functions are recorded per issue. Evidence and limitations must be retained before gate closure. Public articles describing a real repair remain unpublished until QUAL-01 supplies the actual bundle and verifier/tamper output.
