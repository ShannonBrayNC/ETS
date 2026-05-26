# Lantern Stack Issue Sweep - 2026-05-26

## Operating log

This log tracks cross-repo Lantern stack work so progress survives interruptions.

Stack repos under review:

- `ETS`
- `signalforge`
- `christina-assistant`
- `OpsHelm`
- `EchoLiving`
- `EchoMedia-ContentEngine`
- `EchoChamber`
- `echocode`
- `echocode-pipeline`
- `echocode-platform`
- `Lantern-Civic`

## Completed in this run

- Initialized cross-repo sweep log.
- Confirmed `C:\GitHub\lantern` is a checkout of `EchoMedia-ContentEngine`, not a separate GitHub repo named `lantern`.
- Enumerated open Lantern/recommendation issue queues across ETS, SignalForge, Christina, OpsHelm, EchoLiving, Content Engine, EchoCode Platform, and Lantern Civic.
- Found dirty local worktrees that need care before implementation:
  - `signalforge`: deleted `.env.example`
  - `christina-assistant`: active `chore/vitest-audit-review` changes
  - `OpsHelm`: active merge conflicts
  - `echoliving`: modified `package-lock.json`
  - `EchoMedia-ContentEngine`: many active content/platform changes
  - `EchoChamber`: modified `.gitignore`
  - `echocode-platform`: active Phase 11 changes and generated artifact deletions
- ETS: implemented Lantern verification API and tamper demo before this log was created:
  - `POST /api/v1/lantern/verify`
  - local recommendation tamper demo script
  - walkthrough docs
  - expanded Lantern verifier and API tests
  - validation: `python -m ruff check .` passed
  - validation: `python -m pytest -q` passed with 284 tests
  - closed ETS issues `#60` and `#61`
- ETS: synced branch `codex/lantern-stack-sweep-20260526` to origin with commit `f684fd9`.
- ETS `#44`: added `docs/lantern-adapter.md` contract and `tests/unit/test_lantern_adapter_docs.py`.
  - validation: `python -m pytest tests\unit\test_lantern_adapter_docs.py -q` passed
  - validation: `python -m ruff check .` passed
  - validation: `python -m pytest -q` passed with 285 tests
- ETS `#45`: added deterministic support-intelligence adapter models, `POST /api/v1/lantern/support/analyze`, structured artifact bundle output, approval-gated customer outputs, memory observations, KB candidate metadata, and API/unit tests.
  - validation: `python -m pytest tests\test_lantern_support_adapter.py tests\integration\test_api.py -q` passed
  - validation: `python -m ruff check ets\lantern.py ets\api\app.py tests\test_lantern_support_adapter.py tests\integration\test_api.py` passed
  - validation: `python -m pytest -q` passed with 288 tests
  - validation: `python -m mypy` passed
- ETS `#46`: added Lantern recommendation export/update models, `GET /api/v1/lantern/recommendations`, `POST /api/v1/lantern/recommendations/{recommendationId}`, duplicate keys, sprint candidate export, docs, and tests.
  - validation: `python -m pytest tests\test_lantern_recommendations.py tests\integration\test_api.py -q` passed
  - validation: `python -m mypy` passed
  - validation: `python -m ruff check .` passed
  - validation: `python -m pytest -q` passed with 291 tests
- SignalForge `#36`: reviewed existing Lantern envelope, registry, adapter registry, and intake contracts; fixed contract validation blockers.
  - branch: `codex/signalforge-lantern-contract-fixes`
  - commit: `78dc211`
  - fix: Pydantic after validators now use safe assignment in Lantern contract gates
  - fix: review-cycle duplicate linking now requires explicit `dedupeKey`, avoiding accidental collapse of distinct same-title recommendations
  - validation: `python -m pytest src\shared\tests\test_lantern_contracts.py src\shared\tests\test_lantern_intake.py -q` passed
  - validation: `python -m pytest -q` passed with 26 tests
  - validation: `python -m mypy src\shared\signalforge_contracts` passed
  - validation: `npm test` passed after local `npm install`
  - note: pre-existing local `signalforge` deletion of `.env.example` was not staged or committed
  - closed: `ShannonBrayNC/signalforge#36`
- SignalForge `#20`: reviewed recommendation registry and scheduled review orchestration against acceptance criteria.
  - covered by existing docs: `docs/architecture/recommendation-registry.md`, `docs/lantern/RECOMMENDATION_REGISTRY.md`
  - covered by existing code: `recommendations.py`, `review.py`, `local_registry.py`, `review_runner.py`
  - closed using validation from branch `codex/signalforge-lantern-contract-fixes`
  - closed: `ShannonBrayNC/signalforge#20`
- SignalForge `#25`: reviewed Lantern PM Christina, SignalForge, GitHub adapter contracts and downstream handoff filter.
  - covered by existing scaffold contracts/adapters/gates under `scaffolds/lantern-pm/src/lantern_pm`
  - validation: `python -m pytest scaffolds\lantern-pm\src\tests\test_adapters_and_handoff.py -q` passed with 7 tests
  - closed: `ShannonBrayNC/signalforge#25`
- SignalForge `#35`: reviewed consent-first charter, consent model, trust boundary, ecosystem responsibilities, event envelope, registry, and adapter registry docs.
  - covered by existing docs under `docs/lantern`
  - covered by shared contract consent/approval behavior in `src/shared/signalforge_contracts/lantern.py`
  - closed: `ShannonBrayNC/signalforge#35`
- SignalForge `#26`: reviewed Lantern PM storage, handoff audit, and SignalForge mapping.
  - covered by existing scaffold storage, audit, mapping, examples, and Sprint 02 docs
  - validation: `python -m pytest scaffolds\lantern-pm\src\tests\test_storage_and_signalforge_mapping.py -q` passed with 4 tests
  - closed: `ShannonBrayNC/signalforge#26`
- Christina `#73`: added verified recommendation inbox core model and tests.
  - branch: `codex/christina-verified-recommendation-inbox`
  - commit: `91b8370`
  - added mock SignalForge recommendation loading, verified/unverified/blocked lanes, source/target/risk/consent/ETS proof display fields, dry-run external action posture, reason capture for medium/high/restricted reviews, and reviewed work item payload generation back to SignalForge
  - validation: `npm exec vitest run tests/lanternRecommendationInbox.test.ts` passed with 5 tests
  - validation: `npm run build` passed
  - validation: `npm test` passed with 108 tests
  - note: pre-existing local Christina RC worktree edits were left unstaged/uncommitted
  - closed: `ShannonBrayNC/christina-assistant#73`
- Christina `#72`: added six-hour Lantern operating-loop planner, structured summary, sprint candidate output, duplicate/update handling, personal request separation, and documentation.
  - branch: `codex/christina-verified-recommendation-inbox`
  - commit: `b6d3c78`
  - validation: `npm exec vitest run tests/lanternOperatingLoop.test.ts tests/lanternRecommendationInbox.test.ts` passed with 8 tests
  - validation: `npm run build` passed
  - validation: `npm test` passed with 111 tests
  - note: pre-existing local Christina RC worktree edits were left unstaged/uncommitted
  - closed: `ShannonBrayNC/christina-assistant#72`
- Christina `#74`, `#75`, `#76`: implemented scheduled repo-review MVP and opened PR.
  - branch: `codex/christina-verified-recommendation-inbox`
  - commit: `5a8aaf6`
  - PR: `https://github.com/ShannonBrayNC/christina-assistant/pull/77`
  - added six-hour/manual GitHub Actions workflow, `christina.review.json`, PowerShell runner/module, OpenAI Responses API review call with dry-run fallback, issue fingerprint sync, bootstrap script, prompts, docs, and report path
  - validation: `pwsh -NoProfile -Command "Import-Module ./tools/christina/Christina.Review.psm1 -Force"` passed
  - validation: `pwsh -NoProfile -File ./scripts/codex/bootstrap-christina-review.ps1 -Force` passed
  - validation: `pwsh -NoProfile -File ./tools/christina/Invoke-ChristinaRepoReview.ps1 -ConfigPath ./christina.review.json -TargetRepo ShannonBrayNC/OpsHelm -DryRun` passed
  - validation: `npm run build` passed
  - validation: `npm test` passed with 111 tests
  - note: checked official OpenAI Responses API docs for the direct API call shape
  - closed: `ShannonBrayNC/christina-assistant#74`, `#75`, `#76`
- OpsHelm queue review: implementation deferred because local `C:\GitHub\OpsHelm` has active merge conflicts (`AA`/`UU`) and unrelated staged additions.
  - blocked issues in queue: `#30`, `#31`, `#32`, `#33`, `#34`
  - action: leave unmodified until the conflict resolution branch is clean or a separate clean worktree is provided
- EchoLiving `#1`: added root `docs/lantern-adapter.md` documenting capabilities, Lantern Core input payload, output artifacts, guest reply/listing optimization/property onboarding workflows, memory observations, Content Engine handoff, and approval gates.
  - branch: `codex/echoliving-lantern-adapter-doc`
  - commit: `f3d2e7a`
  - validation: `npx tsx --test src/lantern/propertyAction.test.ts` passed with 3 tests
  - validation: `npm run build` passed
  - note: aggregate `npm run test:lantern` fails on an existing harness mismatch because `sanitizePropertyPayload.test.ts` imports `vitest` while root `package.json` does not declare it
  - note: pre-existing local `package-lock.json` modification was not committed
  - closed: `ShannonBrayNC/EchoLiving#1`
- EchoLiving `#2`, `#4`, `#5`: implemented executable Lantern hospitality and property-operations workflows.
  - branch: `codex/echoliving-lantern-adapter-doc`
  - commit: `d417e94`
  - added `src/lantern/hospitalityAdapter.ts` for guest reply, listing optimization, and property onboarding workflow payloads
  - outputs include Lantern action, recommendation id/kind, Christina or Content Engine artifact, memory observation, channel notes, sanitized payload, approval state, and ETS proof placeholder
  - fixed root Lantern test harness to use `node:test` consistently and repaired nested redaction/blocking propagation
  - validation: `npm run test:lantern` passed with 11 tests
  - validation: `npm run build` passed
  - note: pre-existing local `package-lock.json` modification was not committed
  - closed: `ShannonBrayNC/EchoLiving#2`, `#4`, `#5`
- EchoLiving `#3`: added recommendation export and Christina sprint-candidate intake support.
  - branch: `codex/echoliving-lantern-adapter-doc`
  - commit: `dc81df3`
  - added `src/lantern/recommendationRegistry.ts` with SignalForge registry keys, open recommendation export, sprint candidates, dedupe by `dedupeKey` or tracking issue URL, review notes, and status updates
  - updated `docs/lantern-adapter.md` with the recommendation export/query pattern
  - validation: `npm run test:lantern` passed with 15 tests
  - validation: `npm run build` passed
  - note: pre-existing local `package-lock.json` modification was not committed
  - closed: `ShannonBrayNC/EchoLiving#3`
- EchoMedia Content Engine `#100`, `#101`: implemented Lantern reusable content asset adapter and no-provider pipeline from an isolated clean worktree.
  - original checkout note: `C:\GitHub\EchoMedia-ContentEngine` has active local edits and was not modified
  - worktree: `C:\GitHub\EchoMedia-ContentEngine-codex-lantern`
  - branch: `codex/content-engine-lantern-assets`
  - commit: `bb27a83`
  - added root `docs/lantern-adapter.md` covering Lantern inputs, reusable outputs, `opportunity.detected` mapping, approval flow, brand voice, and feedback scaffolding
  - added `services/lantern_content_assets.py` for deterministic source-artifact-to-assets conversion with metadata, traceability, backlog records, channel previews, approval gates, and blocked-rights enforcement
  - added `tests/e2e/test_lantern_content_assets.py`
  - validation: `python -m pytest tests/e2e/test_lantern_content_assets.py -q` passed with 3 tests
  - validation: `python scripts/validate_repo_baseline.py` passed
  - validation: `python -m pytest -q` passed with 6 tests
  - closed: `ShannonBrayNC/EchoMedia-ContentEngine#100`, `#101`
- EchoMedia Content Engine `#102`, `#105`: implemented machine-readable recommendation export, Christina sprint candidates, and RC readiness JSON report.
  - worktree: `C:\GitHub\EchoMedia-ContentEngine-codex-lantern`
  - branch: `codex/content-engine-lantern-assets`
  - commit: `8aaa0c8`
  - added `services/lantern_recommendations.py` with registry export, SignalForge keys, duplicate-key/linked-issue dedupe, sprint candidates, review notes, and status updates
  - added `scripts/export_lantern_recommendations.py`
  - generated `docs/reports/content-engine-recommendation-export-2026-05-26.json` and `docs/reports/rc-readiness-2026-05-26.json`
  - updated `docs/recommendation-registry.md` and `docs/reports/rc-readiness-2026-05-24.md`
  - validation: `python -m pytest tests/e2e/test_lantern_recommendations.py -q` passed with 4 tests
  - validation: `python scripts/validate_repo_baseline.py` passed
  - validation: `python -m pytest -q` passed with 10 tests
  - closed: `ShannonBrayNC/EchoMedia-ContentEngine#102`, `#105`
- EchoMedia Content Engine `#106`: added verified Lantern asset release gate and SignalForge artifact handoff.
  - worktree: `C:\GitHub\EchoMedia-ContentEngine-codex-lantern`
  - branch: `codex/content-engine-lantern-assets`
  - commit: `63e90bc`
  - existing canon registry and consent theme bible are now backed by `services/lantern_verified_assets.py`
  - release gate requires cleared rights, approved human approval state, granted or not-required consent, evidence hash, and ETS proof reference before production-ready release
  - SignalForge `artifact.created` handoff is emitted only for released manifests
  - validation: `python -m pytest tests/e2e/test_lantern_verified_assets.py -q` passed with 5 tests
  - validation: `python -m pytest -q` passed with 15 tests
  - validation: `python scripts/validate_repo_baseline.py` passed
  - closed: `ShannonBrayNC/EchoMedia-ContentEngine#106`
- EchoCode Platform `#35`: onboarded repo for Christina scheduled review loop from an isolated clean worktree.
  - original checkout note: `C:\GitHub\echocode-platform` has active Phase 11 local edits and was not modified
  - worktree: `C:\GitHub\echocode-platform-codex-lantern`
  - branch: `codex/echocode-christina-onboarding`
  - commit: `9926da9`
  - verified Christina control-plane `christina.review.json` already includes `ShannonBrayNC/echocode-platform`
  - added `.christina/repo-profile.json` and `docs/christina-repo-review.md`
  - added duplicate-safe issue fingerprint policy, suggested labels, safe commands, review priorities, and human-approved auto-fix boundaries limited to `needs-codex`
  - added `tests/conftest.py` and `tests/unit/test_christina_repo_profile.py`
  - made `ExecutionLoop` no-provider friendly by skipping GitHub publishing unless app credentials are present
  - declared `PyJWT` dependency and removed an unused `sys` import from `tools/ci_validate.py`
  - validation: `python -m pytest tests/unit/test_christina_repo_profile.py -q` passed with 2 tests
  - validation: `python -m pytest tests/unit -q` passed with 11 tests
  - validation: `python tools/ci_validate.py` passed
  - validation: `python -m ruff check .` passed
  - note: `python -m mypy src` still reports pre-existing missing dependency/stub and `no-any-return` findings outside this onboarding change
  - closed: `ShannonBrayNC/echocode-platform#35`
- Lantern Civic `#10`, `#11`, `#12`: added executable civic orchestration, Christina governance, and ETS trust foundation.
  - repo: `C:\GitHub\Lantern-Civic`
  - branch: `codex/lantern-civic-core-foundation`
  - commit: `8bb0b82`
  - added `pyproject.toml`, package `src/lantern_civic`, docs, and tests
  - `event_bus.py` covers event taxonomy, idempotency, routing, replay, dead-letter handling, approval checkpoints, audit hashes, provenance references, and research mirroring
  - `christina_governance.py` covers civic workflow classification, summarization, confidence, human approval checkpoints, escalation, explainability, AI disclosure, prompt lineage, and research metadata
  - `ets_trust.py` covers consent ledger/revocation, provenance chain reconstruction, AI disclosure, trust scoring, audit export, and replay support
  - validation: `python -m pytest -q` passed with 4 tests
  - validation: `python -m compileall src tests` passed
  - closed: `ShannonBrayNC/Lantern-Civic#10`, `#11`, `#12`
- ETS `#34`, `#35`: added explicit Phase 2 and Phase 3 npm demo entry points.
  - branch: `codex/lantern-stack-sweep-20260526`
  - commit: `eed710b`
  - added `npm run demo:phase2` via `scripts/run_phase2_demo.py`
  - Phase 2 demo covers artifact upload, proof generation, explorer timeline steps, verification, tamper simulation, failed verification, API surface, and Azure immutable-storage deployment path
  - added `npm run demo:phase3` via `scripts/run_phase3_demo.py`
  - Phase 3 demo covers multi-node root sync, signed root exchange, shared evidence verification, divergence injection, divergent node reporting, and explicitly avoids claiming distributed consensus
  - added `tests/unit/test_phase_demos.py`
  - validation: `npm run demo:phase2` passed
  - validation: `npm run demo:phase3` passed
  - validation: `python -m pytest tests/unit/test_phase_demos.py -q` passed with 2 tests
  - validation: `python -m ruff check .` passed
  - validation: `python -m pytest -q` passed with 293 tests
  - note: pre-existing untracked `package-lock.json` was not committed
  - closed: `ShannonBrayNC/ETS#34`, `#35`
- EchoMedia Content Engine `#44`, `#45`, `#46`, `#51`, `#52`, `#53`, `#54`, `#55`: added provider documentation ingestion strategy and no-provider audio/video adapter contracts.
  - worktree: `C:\GitHub\EchoMedia-ContentEngine-codex-lantern`
  - branch: `codex/content-engine-lantern-assets`
  - commit: `49cc561`
  - added `docs/provider-documentation-ingestion.md`
  - added `services/voice_providers.py` with provider-neutral voice request/result/profile contracts, fake provider, Azure Speech mapping, manifest output, and validation gates
  - added `services/video_providers.py` with provider-neutral video request/job/profile contracts, Runway/OpenAI-video/Luma mappings, Kling/Pika planned-blocked profiles, traceability to voice/audio/timing refs, and validation gates
  - added `tests/e2e/test_voice_video_provider_contracts.py`
  - validation: `python -m pytest tests/e2e/test_voice_video_provider_contracts.py -q` passed with 5 tests
  - validation: `python -m pytest -q` passed with 20 tests
  - validation: `python scripts/validate_repo_baseline.py` passed
  - closed: `ShannonBrayNC/EchoMedia-ContentEngine#44`, `#45`, `#46`, `#51`, `#52`, `#53`, `#54`, `#55`
- ETS `#51`, `#52`, `#53`, `#54`, `#55`: added missing dissertation-track deliverables called out in issue comments.
  - branch: `codex/lantern-stack-sweep-20260526`
  - commit: `122e27a`
  - added `docs/dissertation/PROSPECTUS.md`, `LITERATURE_REVIEW.md`, `FORMAL_FOUNDATIONS.md`, `EVALUATION_AND_BENCHMARKS.md`, `ABSTRACT.md`, `DEFENSE_SLIDES.md`, `CONTRIBUTIONS.md`, and `PUBLICATION_PIPELINE.md`
  - added `tests/unit/test_dissertation_deliverables.py`
  - validation: `python -m pytest tests/unit/test_dissertation_deliverables.py -q` passed with 3 tests
  - validation: `python -m ruff check .` passed
  - validation: `python -m pytest -q` passed with 296 tests
  - note: pre-existing untracked `package-lock.json` was not committed
  - closed: `ShannonBrayNC/ETS#51`, `#52`, `#53`, `#54`, `#55`
- OpsHelm blocker review and `#34` resolution: original `C:\GitHub\OpsHelm` checkout remains unsafe for direct edits because it has unresolved `AA`/`UU` conflicts, so an isolated clean worktree was used.
  - recommendation: finish or abort the merge in `C:\GitHub\OpsHelm` separately; for unrelated issue work, continue using clean worktrees from `origin/main`
  - worktree: `C:\GitHub\OpsHelm-codex-christina`
  - branch: `codex/opshelm-christina-onboarding`
  - commit: `7f4f303`
  - added `.christina/repo-profile.json`, `docs/christina-repo-review.md`, and `services/christina/repoProfile.test.ts`
  - added `npm run test:christina`
  - verified Christina control-plane config already includes `ShannonBrayNC/OpsHelm`
  - validation after `npm ci`: `npm run test:christina` passed with 2 tests
  - validation: `npm run test:lantern` passed with 5 tests
  - validation: `npm run test:ingestion` passed with 10 tests
  - closed: `ShannonBrayNC/OpsHelm#34`
- OpsHelm `#30`, `#31`, `#32`, `#33`: completed from the isolated clean worktree while leaving the conflicted original checkout untouched.
  - recommendation carried out: continue unrelated fixes from clean worktrees until `C:\GitHub\OpsHelm` merge conflicts are resolved or aborted separately
  - worktree: `C:\GitHub\OpsHelm-codex-christina`
  - branch: `codex/opshelm-christina-onboarding`
  - commit: `730b3b9`
  - added `docs/lantern-adapter.md` with stable `support.analysis.requested` payload, artifact metadata contract, sample shim, support feature surface, SignalForge/Christina routing, and customer-send approval gate
  - expanded `services/lantern/opshelmLanternAdapter.ts` with request creation, artifact refs, read-only/draft/customer-facing action classification, ETS proof references, missing-proof quarantine, and Christina sprint candidate export
  - added tests for valid support-analysis payloads, approval-gated customer drafts, medium-risk drafts, mock ETS proof refs, required missing proof quarantine, and deduplicated Christina sprint export links/status/buckets
  - validation: `npm run test:lantern` passed with 9 tests
  - validation: `npm run test:christina` passed with 2 tests
  - validation: `npm run test:ingestion` passed with 10 tests
  - validation: `npx tsc --noEmit` passed
  - closed: `ShannonBrayNC/OpsHelm#30`, `#31`, `#32`, `#33`

## In progress

- Sweep follow-up complete for newly requested open items.

## Not completed yet

- The original `C:\GitHub\OpsHelm` checkout still has unresolved merge conflicts and should be resolved or abandoned separately before it is used for future work.
- A post-closure GitHub sanity check still shows broader backlog in OpsHelm, SignalForge, Christina, ETS, EchoMedia Content Engine, and Lantern Civic. Those are sprint, epic, production-hardening, or newly generated items outside the current recommended Lantern/Christina sweep list.

## Recommended issue queue

### ETS

No currently tracked high-priority ETS Lantern starter items remain in this sweep queue.

### SignalForge

No currently tracked high-priority SignalForge Lantern starter items remain in this sweep queue.

### Christina Assistant

No currently tracked high-priority Christina starter items remain in this sweep queue.

### OpsHelm

No currently tracked high-priority OpsHelm Lantern/Christina starter items remain in this sweep queue.

### EchoLiving

No currently tracked high-priority EchoLiving Lantern starter items remain in this sweep queue.

### EchoMedia Content Engine

No currently tracked high-priority EchoMedia Content Engine Lantern starter items remain in this sweep queue.

### EchoCode Platform

No currently tracked high-priority EchoCode Platform Lantern starter items remain in this sweep queue.

### Lantern Civic

No currently tracked high-priority Lantern Civic starter items remain in this sweep queue.
