# ETS Desktop Developer Edition: Store readiness and SDK plan

Review date: 2026-10-28

Baseline: [`aae2d598`](https://github.com/ShannonBrayNC/ETS/commit/aae2d598c1ed967a60b76b226ba4bf27eeb12d21) (main, including #948)

Status: **review and proposed implementation backlog; no Developer Edition build or Store approval**.

## Recommendation and decision boundary

Build **ETS Desktop Developer Edition** as an offline-first developer workbench
that **includes the existing strict verifier**, a guided local evidence sandbox,
and a genuinely usable, versioned SDK kit. Reuse the Python protocol/verifier
implementation and current Windows host rather than starting a second verifier
or a .NET UI rewrite. Ship Python as the reference SDK, with the already-existing
.NET and TypeScript Application SDKs as companion packages and samples.

Prefer the existing MSIX approach: a self-contained, standard-user desktop app
with bundled application runtime, verifier and SDK assets. User-installed Python/Node toolchains, the .NET SDK,
Git, Docker, an account and a hosted service must not be prerequisites for
opening the workbench, running its built-in example, or verifying a bundle.
Running exported language-specific source projects is a separate action with
explicit toolchain prerequisites. The GUI still requires WebView2; the standalone
frozen CLI does not. “Self-contained” here refers to the application Python
runtime, not an already-bundled browser runtime.

This extends, rather than replaces, the [go-to-market plan](GO_TO_MARKET_PLAN.md):
the free standalone Verifier remains the simplest recipient/auditor product;
Developer Edition adds authoring/integration tools. Enterprise Edge collection,
Fleet, Gateway, hosted subscriptions and appliance operations remain separate.
**Recommended packaging:** a separately identifiable Developer Edition SKU built
from the same verifier components, able to coexist with the standalone Verifier.
A single Store listing with a developer mode is an alternative product decision,
not an implemented capability. Approve SKU/name, pricing, support and identity
before reserving or changing anything in Partner Center. Do not infer a price
for the Developer Edition from the free-verifier commitment.

This document does not authorize implementation, package publication, signing,
Store submission or merging. Items called **proposed**, **open** or **not run**
are requirements, not features or acceptance results.

## What exists, and what does not

All source paths below refer to the baseline above; later commits need a new
compatibility/evidence review. An implemented component is not a release gate pass.

| Component | Evidence in the repository | Current limit / Developer Edition work |
| --- | --- | --- |
| Windows desktop | [`ets/desktop/host.py`](../../ets/desktop/host.py), [`controller.py`](../../ets/desktop/controller.py), [`index.html`](../../ets/desktop/index.html) | pywebview/WebView2 local UI; real file pickers, strict subprocess verification and reports. No developer project manager, SDK-kit export or guided authoring workflow |
| Shared verifier | [`ets/verifier/cli.py`](../../ets/verifier/cli.py), [`service.py`](../../ets/verifier/service.py), [`input.py`](../../ets/verifier/input.py) | Strict signed offline verification, bounded CLI JSON input, explicit result classes. Reuse this implementation; the full [proposed C3 contract](../core/ETS_CORE_C3_OFFLINE_VERIFIER_CONTRACT.md) is not implemented |
| Report contract | [`ets/reports/strict.py`](../../ets/reports/strict.py) | `ets.offline_report.v1`, JSON/Markdown/HTML; fresh computed outcomes and no-overwrite publication. Not a signed proof or bundle |
| Local Python SDK | [`ets/sdk/local.py`](../../ets/sdk/local.py), [`ets/sdk/models.py`](../../ets/sdk/models.py) | Validates/hashes/appends evidence and verifies event hashes/inclusion; `append_evidence` returns a `LogEntry`, not the remote SDK receipt. No packaged desktop sandbox orchestration |
| Remote Python SDK | [`ets/sdk/client.py`](../../ets/sdk/client.py) | Sync/async capture, retrieval, bundles, explicit API compatibility check, strict offline/online verification. Uses the shared verifier, not another trust engine |
| .NET and TypeScript SDKs | [`EtsClient.cs`](../../sdk/dotnet/Ets.Application/EtsClient.cs), [`client.ts`](../../sdk/typescript/src/client.ts) | Health/version/compatibility, capture, event/bundle/proof retrieval. **No full strict offline-verifier implementation in either client**; route exported bundles through the common verifier |
| Canonicalization | [`conformance/sdk/v1`](../../conformance/sdk/v1/README.md), [cross-language scope](../sdk/CROSS_LANGUAGE.md) | Existing vectors cover a bounded corpus, not arbitrary payload parity or RFC 8785/JCS compliance. `Ets.Evidence` is a different Evidence Object library, not the Application SDK |
| Local server profile | [`compose.sdk-dev.yml`](../../compose.sdk-dev.yml), [Dev environment](../sdk/DEV_ENVIRONMENT.md) | Docker, loopback HTTP, SQLite volume, `local_header`, unsigned tree heads. This is optional developer infrastructure, **not** the bundled desktop sandbox |
| Samples | [Python quickstart](../../examples/sdk/python/quickstart.py), [Chess walkthrough](../../examples/sdk/chess/README.md) | Existing samples require the Dev endpoint and explicitly relax signature policy. They are not strict signed desktop round-trip acceptance tests |
| Windows package | [`desktop.spec`](../../packaging/windows/desktop.spec), [`verifier.spec`](../../packaging/windows/verifier.spec), [`msix_layout.py`](../../packaging/windows/msix_layout.py) | Frozen Python runtime plus separate verifier, development identity `ETSVerifier.Development`, x64, configured Windows 11 floor, `runFullTrust`; WebView2 remains external. SDK assets are not currently bundled |
| SDK release preparation | [release matrix](../sdk/RELEASE_MATRIX.json), [release process](../sdk/RELEASE.md), [`sdk-release-candidate.yml`](../../.github/workflows/sdk-release-candidate.yml) | Package builds/manifest/SBOM workflow exists. Source versions and workflows do **not** establish registry availability, completed publisher configuration or release approval |

### Lenovo and current verifier evidence

[PR #948](https://github.com/ShannonBrayNC/ETS/pull/948) added a `0.1.1.0` MSIX
qualification increment without changing the `0.1.0a1` application version.
[PR #949](https://github.com/ShannonBrayNC/ETS/pull/949), open/unmerged when this
review began, records operator-attested Lenovo installation, disconnected
verification/export, reinstall, upgrade/downgrade, keyboard, Narrator and 200%
scaling results. It also records missing exact OS/WebView2/elevation/signed-digest
and clean-machine evidence and a WACK handoff. Treat that PR as the source for
those operator reports; do not overwrite it or restate its tests as unperformed.

Neither the user's statement that testing is wrapping up, these attestations,
nor Windows Server CI establishes Developer Edition acceptance. Developer
Edition adds new workflows/payloads and needs its own exact-candidate record.
Continue the [verifier release gap list](MICROSOFT_STORE_RELEASE_GAPS.md) and
[Lenovo qualification](LENOVO_WINDOWS_QUALIFICATION.md); avoid a second,
contradictory verifier qualification ledger.

## Product boundary and first-release experience

| Included in proposed v1 | Explicitly outside v1 / optional separate installation |
| --- | --- |
| Existing strict offline verifier and report export | Always-on Edge collector, machine service or driver |
| New/open local project; inspect schema, hashes, receipt and checkpoint | Fleet enrollment, administrative machine identity, production key custody |
| Guided synthetic event → local commitment → bundle → verification → report | Automatic collection of arbitrary files, telemetry, Graph/SharePoint or device data |
| Offline docs, reference schemas, golden fixtures, SDK archives and runnable sample source | Bundled IDE, compiler farm, Docker engine, automatic machine-global Python/Node/.NET/PATH changes |
| Explicit export to a user-chosen directory; project-local dependency instructions | Hosted account, subscription, Azure access, tenant consent or internet required for core offline use |
| SDK/verifier/version diagnostics and clear trust-policy display | Production readiness, current revocation/freshness, physical truth or completeness claims |

The acceptance journey is: install → launch without sign-in → create a synthetic
project → inspect its evidence/commitment → export a bundle → verify with the
included strict verifier → inspect each check and limitations → export report →
export the SDK/sample kit and reproduce the result outside the app. A website
link alone does **not** satisfy “with an SDK.”

A project is a user-controlled directory with proposed versioned project metadata,
synthetic event inputs, local ledger/checkpoints, exports and explicit trust
configuration. Choose locations through native UI; never silently scan/import
customer directories. Store mutable projects outside the installation directory.
Do not call this a security sandbox: the proposed full-trust application runs with
the user's rights. Here “developer sandbox” means isolated development data and
non-production policy, not OS containment of arbitrary code.

## Architecture: one verification implementation

```text
Bundled local HTML / native dialogs
    │ narrow allowlisted controller (no generic shell or arbitrary file bridge)
    ├── existing strict verifier child process ── ets.verifier.service ── ets.core
    ├── proposed guided sandbox worker ── ets.sdk.local / core / local SQLite
    └── proposed SDK-kit exporter ── read-only packaged assets → chosen project

External Python / .NET / TypeScript project
    ├── optional HTTPS ETS endpoint (existing SDK contract)
    └── portable bundle → same bundled verifier CLI → structured outcome/report

Optional Docker Dev endpoint / enterprise Edge / hosted services remain separate.
```

1. Preserve `DesktopAPI.verify()`'s fixed command/argument-list subprocess path,
   timeout, credential-environment removal and response checks. Never expose a
   generic `run(command)` bridge or execute code from an evidence bundle.
2. Keep strict verification independent of project authoring. Run it over the
   exported bytes, not an author's cached success flag or embedded
   `verification_result`. Preserve required-signature policy in the verifier pane.
3. Build the guided sandbox from existing core/SDK/store code. Prefer no listening
   socket for initial offline functionality. If a worker is added, use bounded
   structured IPC, explicit lifetime/cancellation and per-user/project access.
   The current app has a verifier subprocess, **not** this proposed sandbox worker.
4. Treat a future optional loopback API as a separate security qualification:
   authentication, origin/CSRF protection, binding, port collision, quotas,
   shutdown and exact packaged-Windows IPC behavior. Loopback alone is not
   authentication; do not ship debugging exemptions or start a machine service.
5. Keep the local trusted UI separate from arbitrary project HTML, Markdown or
   remote pages. Retain safe rendering, navigation restrictions and a narrowly
   exposed native bridge; do not execute untrusted project scripts in WebView2.
   [Microsoft WebView2 security guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/security)
6. Core protocol code must remain independent of UI, API and persistence runtime
   dependencies, as required by [CONTRIBUTING](../../CONTRIBUTING.md).

### Development signatures and trust labels

Use two clearly different examples:

- **Unsigned local commitment:** reproduce the existing Dev profile; strict
  verification remains indeterminate when signature/trust is absent. A separate
  development-policy demonstration may explain `--allow-unsigned`, but must not
  present it as trusted verification or silently enable it in the verifier UI.
- **Signed synthetic round trip:** a proposed explicitly initiated local sample
  issuer generates a non-production key, exports public trust material separately,
  and signs a sandbox checkpoint. Require deliberate trust selection and display
  “local development issuer,” expected log ID, key ID and checkpoint-only standing.
  Protect per-user private material, define deletion/reset and never export it
  with the normal sample kit. Bundled deterministic test fixtures are public test
  identities, never default trusted issuers or production signing credentials.

A matching signature establishes integrity relative to the selected key/policy;
selection of a local key does not authenticate a real organization. Neither a
signature nor `committed_local` proves semantic/physical truth, completeness,
authorization or current standing. Offline verification cannot establish fresh
revocation/continuity beyond the supplied trust/checkpoint material.

## SDK contents, API/CLI surface and compatibility

### Deliver an offline SDK kit, not an embedded developer toolchain

The proposed versioned kit contains the Python wheel/sdist, .NET `.nupkg`, npm
`.tgz`, their license notices, API/CLI reference, schema/contract documentation,
conformance vectors, deterministic fixtures, and Python/.NET/TypeScript sample
projects. Record exact artifact sizes/hashes, source commit and runtime minima
in a kit manifest. Pin sample dependencies and include project-local restore
instructions. Registry copies should match these reviewed versions and the
[SDK release manifest](../sdk/RELEASE.md), with provenance verified where available.
Do not describe all registry artifacts as cryptographically signed unless the
release actually supplies and verifies those signatures/attestations.

“Offline kit” means the app can export/read the kit without network access. A
fully disconnected **external** sample build additionally needs a supported
user-installed toolchain and a complete, license-reviewed dependency cache/feed.
Either supply and test those dependencies or disclose precisely which restore
step needs internet. Do not promise arbitrary SDK project builds on a machine
with no compiler/runtime. The bundled app's own Python runtime is private and
must not be advertised as a general-purpose system Python installation.

Use export/copy with consent and no overwrite; never run package-manager scripts,
restore packages, alter global PATH or install a toolchain as a side effect of
opening a bundle. Show optional install/restore commands before the developer
executes them. Registry publishing remains a separate approved release action.

### Source-backed compatibility matrix

| Surface | Current source version / contract | Proposed Developer Edition support and evidence required |
| --- | --- | --- |
| Desktop MSIX | Verifier engineering package `0.1.1.0`; Windows 11 x64 configured, not a Developer Edition version | Allocate a distinct approved identity/version; test coexistence, signed lifecycle and exact supported OS builds. ARM64 not promised |
| Bundled CLI / Python runtime | `lanternprotocol-ets` / verifier `0.1.0a1`; Python 3.12+ source requirement | Pin verifier/runtime to app release; expose CLI version and JSON contract; test the actual frozen binary under package identity |
| Python Application SDK | `lanternprotocol-ets==0.1.0a1`; `ets.application.sdk.v1` | Reference local/sync/async integration and strict verifier reuse; test wheel installation in a fresh project environment |
| .NET Application SDK | `LanternProtocol.ETS.Application` `0.1.0-alpha.1`; `net8.0` | Existing client plus new complete sample; export bundle and invoke shared verifier, not a claimed native .NET strict-verifier API |
| TypeScript Application SDK | `@lanternprotocol/ets-sdk` `0.1.0-alpha.1`; Node `>=22.14.0` | Existing client plus new complete sample; same bundle/CLI boundary; do not imply browser runtime support solely from TypeScript source |
| Service API / receipt | REST `v1`; `ets.sdk.event_commit_receipt.v1`, state `committed_local` | Explicit compatibility check before remote work; no invisible write retries; never equate receipt with independent verification |
| Event / bundle / inclusion | `ets.event.v1`, `ets.proof_bundle.v1`, `ets.inclusion_proof.v1` | Preserve strict supported schemas and defaults; reject unknown versions. Canonical source: [models](../../ets/core/models.py), [bundle](../../ets/core/bundle.py), [proofs](../../ets/core/proofs.py) |
| Trust / verifier / report | `ets.verifier_trust.v1`, `ets.verifier.v1`, `ets.offline_report.v1` | Ed25519 and PS256 supported by strict offline path; test selected trust/log policy and report fidelity; do not map legacy certificate output to strict success |
| Developer project / kit metadata | **Not implemented or frozen** | Define separate versioned schemas and migration/backup rules; do not invent a current protocol identifier |

The [release matrix](../sdk/RELEASE_MATRIX.json) remains authoritative for SDK
package names/versions. MSIX package versions, application SemVer/prerelease
versions and protocol identifiers are separate axes; `0.1.1.0` does not mean SDK
v1.1. Registry publication was not established by this review.

Proposed release policy: publish the exact tested app/CLI/kit/SDK matrix for each
candidate; keep previous supported bundle schemas readable or fail explicitly
as unsupported. Qualify current SDK → current verifier, previous supported SDK →
current verifier, and current bundle → previous verifier (supported or explicit
unsupported, never false success). Review schema drift and project migrations
before Store auto-updates. Retain prior SDK versions for pinned CI projects;
do not replace their dependencies during an app update.

### Public CLI contract and result handling

Use existing `ets-verify offline <bundle> --trust-store <trust> --expected-log-id
<log> --report <new-path> --report-format json|markdown|html`. See the
[CLI reference](../../ets/verifier/README.md) for actual syntax and limits.
The CLI family remains **0/1/2**, not the proposed C3 exit-code allocation:

| JSON status | Current CLI exit | Developer consumer behavior |
| --- | --- | --- |
| `valid` | 0 | Accept only with `valid=true`, expected policy, and explicit limitations |
| `invalid` | 1 | Fail; never export a successful badge |
| `indeterminate` | 2 without trust-store argument, otherwise 1 | Missing trust/signature is not verified |
| `unsupported` / `malformed` / `resource_limit` | 2 | Preserve distinction and actionable reason code |
| Report publication failure | 2, `status=error` plus `verification_outcome` | Verification and export success are separate states |

Do not hard-code paths inside versioned `WindowsApps`. Propose a uniquely named
app-execution alias for developer CLI use, documented as optional/user-disableable;
handle alias collision/disabled state and test it before claiming shell support.
The current manifest has **no execution alias**. Provide an explicit verified
portable CLI distribution only if separately packaged/licensed/qualified; copying
one EXE out of the frozen directory is not supported.
[Microsoft app-execution aliases](https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/desktop-to-uwp-extensions#start-your-application-by-using-an-alias)

### Required sample set

1. **No-server signed sample:** generate synthetic metadata, append through local
   SDK/core, export a bundle, select separate sample trust, then run the included
   strict verifier and export its report. Exact serialized bytes are the handoff.
2. **Negative variants:** alter event bytes; wrong log; missing/revoked/untrusted
   key; unsupported schema/algorithm; malformed/oversized/deep JSON. Compare SDK,
   bundled CLI and desktop result class/claim boundaries, not volatile timestamps.
3. **Python/.NET/TypeScript integration:** compatibility check, capture receipt,
   bundle export, common CLI verification and report consumption. Include a
   reproducible signed local test issuer/endpoint fixture, or label the existing
   unsigned Docker example's expected strict result as indeterminate. Do not
   upgrade its result to trusted success with `--allow-unsigned`.
4. **Optional hosted example:** HTTPS, one auth mode, production scope from verified
   claims, cancellation/errors and explicit retry policy. Use placeholder secrets;
   no tenant/credential is required for the offline examples.

## Microsoft Store package and release work

These are requirements checked against Microsoft documentation on 2026-10-28,
plus explicitly labeled ETS recommendations. Recheck at submission. Store review,
not this assessment, decides acceptance.

| Area | Required action / choice | Authority or existing ETS evidence |
| --- | --- | --- |
| Distribution | **ETS recommendation:** extend MSIX; keep read-only payload and per-user workspaces. MSI/EXE remains a supported alternative if a real constraint warrants it, not a presumed requirement for SDK tools | [Distribution choices](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path), [package behavior](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes) |
| Identity and version | Obtain approved Partner Center Name, Publisher and PublisherDisplayName; replace engineering-only identity through reviewed build configuration; use valid increasing four-part MSIX versions | [Identity details](https://learn.microsoft.com/en-us/windows/apps/publish/view-app-identity-details), [MSIX requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements) |
| Signing | Store re-signs MSIX after certification; no purchased CA certificate is required solely for MSIX Store submission. Sideload test candidates still require approved signing/trust setup. Never ask for a private key in chat | [MSIX signing requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements), [ETS signing procedure](WINDOWS_SIGNING_QUALIFICATION.md) |
| Capabilities | Justify current `runFullTrust`; full trust is not administrator elevation or AppContainer isolation. Do not add elevation/services/drivers for the developer sandbox | [Capability declarations](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations). Technical MSIX service support does not establish Store eligibility |
| Runtime | Qualify WebView2 discovery/provisioning/missing-runtime recovery. Evergreen standalone supports offline preparation; a bootstrapper needs network; Fixed Version moves runtime servicing to ETS. Pick and test a strategy, not an assumed Store prerequisite install | [WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |
| Accurate listing and SDK acquisition | Describe developer functionality, external toolchain requirements and offline limitations. No hidden post-review functionality. Downloaded code is not categorically banned; review any SDK/dependency acquisition against consent and described behavior | [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies), especially 10.1.5 and 10.2.2–4 |
| Privacy and testability | Supply a privacy policy for this Win32/Desktop Bridge app, support details, age ratings/markets, screenshots and accurate claims. Give reviewers synthetic fixtures and complete offline steps; no customer account needed for core flow | [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies), especially 10.3 and 10.5.1; [current gap list](MICROSOFT_STORE_RELEASE_GAPS.md) |
| Certification | Run current WACK on the exact intended package/client; review failures, then retain Partner Center validation/certification results. WACK success is not Store approval | [Certification process](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-certification-process) |
| MSI/EXE fallback only | If selected, use version-specific immutable direct HTTPS standalone installers, silent installation and required CA signing of installer/PE files; own updates and resubmit changed installer URLs. Do not apply this installer rule as a blanket runtime-download ban | [MSI/EXE package requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msi/app-package-requirements) |

### WebView2 and SDK-archive qualification details

Retain Evergreen as the initial recommendation, consistent with the existing
verifier gap list, but qualify its delivery before claiming a clean offline
install. Test (a) Evergreen present plus disconnected launch, (b) runtime absent
with actionable recovery, (c) disconnected preparation using the approved
standalone runtime installer, and (d) runtime update regression. If the owner
requires first installation and GUI launch with no pre-provisioned runtime and
no network, evaluate a bundled Fixed Version runtime separately for licenses,
size, patching and packaging. Neither strategy has been qualified by this review.
Set or verify a writable per-user WebView2 user-data folder; an attempted write
beside the protected installed EXE must not break startup.
[Microsoft user-data-folder guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/user-data-folder)

Qualify exported SDK archives against actual WACK results and intended device
support. Do not advertise Windows S mode or apply MSI/EXE's all-PE CA-signature
rule indiscriminately to MSIX; Desktop Bridge tests include optional checks.
[Desktop Bridge certification tests](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-desktop-bridge-app-tests)
Store package signing authenticates distribution, not an evidence issuer or the
truth of ETS results.

No change to the existing enterprise MSI choice is implied. The recommendation
avoids unattended services because they are outside this product's scope and
would create unnecessary operational/review obligations, not because all MSIX
services are technically impossible.

## Security, privacy, licensing and supply chain

- **Untrusted inputs:** retain byte/nesting/node bounds, strict JSON parsing,
  schema/algorithm fail-closed handling, render escaping, subprocess timeouts,
  no-overwrite output and trust anchors outside bundles. The current CLI limits
  are not automatically inherited by new in-process SDK/UI paths; test equivalent
  bounds there. Never open project hooks/scripts merely to inspect a project.
- **Workspace custody:** consent before import/export; project allowlisting,
  path traversal/reparse-point protection, byte quotas, cancellation/recovery and
  migration backups. Preserve user project/evidence/report files across updates
  and uninstall; separately document app-local cache/settings cleanup.
- **Credentials/keys:** no production credentials, global trusted roots or bundled
  private signing keys. Non-production issuer keys stay user-protected, outside
  package/sample exports, with clear rotate/reset/delete controls. Optional remote
  secrets need OS-protected storage, redacted diagnostics and explicit endpoints.
- **Privacy:** default to local processing; never upload evidence, file paths,
  trust keys, project content or raw logs for analytics by default. Document app
  diagnostics separately from WebView2/runtime/Store update traffic. Provide
  opt-in/export/redaction controls and retention/deletion statements that match
  actual behavior; do not claim the whole OS is network-silent from an offline
  verifier test. No real customer data in fixtures or certification attachments.
- **Licenses:** reconcile [LICENSE](../../LICENSE), [NOTICE](../../NOTICE), SDK
  package metadata and all shipped Python/native/WebView2/pywebview components,
  SDK archives, transitive dependencies and sample assets. Have a named reviewer
  approve redistribution obligations and customer notices. Apache-2.0 project
  metadata is not approval for every transitive artifact or existing IP gate.
- **SBOM/provenance:** create a runtime SBOM for the actual MSIX payload **and** an
  SDK-kit SBOM with transitive dependency/architecture/version coverage. The
  existing [dependency inventory](WINDOWS_DEPENDENCY_EVIDENCE.md) is unreviewed
  build-environment evidence, not a runtime SBOM. Link source/build commit,
  package/kit/fixture hashes, signatures/attestations and security dispositions.
  The SDK candidate workflow skips attestations on PRs; a green PR is not signed
  release provenance. Apply [release/IP gates](../release/PUBLIC_RELEASE_CHECKLIST.md).
- **Servicing:** assign owners for frozen Python, cryptography, desktop bridge,
  WebView2 strategy and language packages; monitor applicable vulnerabilities,
  retain explicit exceptions, and retest after runtime updates. Store updates
  must not mutate pinned projects or silently change sample trust policy.

## Acceptance matrix: evidence required before calling it ready

Use the existing [qualification record](WINDOWS_RELEASE_QUALIFICATION_RECORD.md)
for the shared Windows gates and append these Developer Edition gates to a
candidate-specific copy. Record PASS/FAIL/NOT RUN, exact source/MSIX/kit hashes,
OS/runtime/toolchain versions, test command/fixture, output and accountable tester.
**Every Developer Edition row below is NOT RUN: no such candidate exists yet.**
Existing component tests are supporting evidence only.

| ID | Gate and cases | Pass evidence / current supporting source |
| --- | --- | --- |
| D1 | Clean standard-user app startup and built-in signed sample without Python/Node/.NET SDK/Git/Docker/account; internet disconnected | Installed identity, OS/tool inventory and blocked-network workflow recording; current [desktop candidate](WINDOWS_DESKTOP_CANDIDATE.md) tests are a starting point |
| D2 | SDK authoring → exact bundle bytes → bundled strict verifier → JSON/Markdown/HTML report | Hashes and expected result/policy for local signed, unsigned and tampered variants; sample trust never installed globally |
| D3 | Python/.NET/TypeScript project reproduction; language/runtime minima and fresh environments | Per-language build/test logs, package hashes and common verifier parity; distinguish offline pre-provisioned dependencies from online restore |
| D4 | Trust/error/input coverage | Six strict result classes, wrong log, bad signature, missing/revoked/expired key, unsupported schema/algorithm, duplicate JSON, oversized/deep/invalid Unicode; tests in [verifier service](../../tests/unit/test_verifier_service.py), [input](../../tests/unit/test_verifier_input.py), [reports](../../tests/unit/test_verifier_strict_reports.py) |
| D5 | API/wire/hash compatibility and migrations | Release matrix checks, expanded cross-language numeric/Unicode/bundle vectors, current/previous supported versions, explicit unsupported errors; no arbitrary payload parity claim from existing corpus |
| D6 | Installed CLI integration | Alias enabled/disabled/collision, spaces/non-ASCII paths, shell exit/JSON/report contract, argument injection and cancellation; no hard-coded WindowsApps location |
| D7 | Workspace/bridge boundaries | No arbitrary code execution, no external UI navigation into bridge, no cross-project key leakage, safe paths/quotas/recovery, read-only inputs and unwritable outputs; prior output preserved |
| D8 | App lifecycle/coexistence | Standalone Verifier + Developer Edition side by side; signed install, upgrade, ordinary downgrade rejection, reinstall, user-data hashes before/after uninstall; interrupted project migration recovery |
| D9 | Usability/accessibility | Real dialogs, keyboard, Narrator, 200% scaling, narrow window; long operations/cancel, repeated clicks, stale results cleared; test new authoring/export UI, not only existing verifier |
| D10 | Supported OS/runtime/architecture | Windows 11 x64 exact builds first; WebView2 absent/present/update paths; other Windows versions/ARM64 only after native qualification |
| D11 | Distribution review | Final payload + SDK-kit SBOM, notices/license sign-off, vulnerability dispositions, hashes/provenance and no secrets; existing release/IP approvals |
| D12 | Store submission | Approved production identity, capability rationale, truthful listing/privacy/support, reviewer instructions, exact-candidate WACK and Store certification decision |

Required repository gates include the normal [CI workflow](../../.github/workflows/ci.yml),
[SDK cross-language tests](../../.github/workflows/sdk-cross-language.yml),
[SDK candidate packaging](../../.github/workflows/sdk-release-candidate.yml) and
[Windows candidate workflow](../../.github/workflows/windows-verifier-candidate.yml)
when the corresponding implementation changes. Current path filters do not run
all these workflows for a documentation-only change; absence of a run is not a
pass. A new Developer Edition pipeline must add round-trip/kit/installed-package
gates rather than simply inheriting the verifier artifact name.

## Phased backlog and decision owners

Owners below are **roles to assign**, not people who have accepted work. No dates,
budgets or estimates are approved. Each phase exits on retained evidence, not
number of PRs or green source-unit tests.

| Phase / priority | Deliverables and dependencies | Proposed owner role | Exit condition / current status |
| --- | --- | --- | --- |
| 0 / P0 — scope and baseline | Choose separate SKU versus shared listing, free/paid policy, Windows support, WebView2 strategy, initial language commitments; reconcile Lenovo/#949 evidence and existing verifier release gaps | Product owner + Windows release owner | Written decisions; exact shared verifier baseline. **OPEN**; do not wait for this doc to declare device results |
| 1 / P0 — SDK/verifier contract | Freeze kit/project metadata, public CLI integration, schema/result compatibility; design signed synthetic fixture and local key lifecycle; expand conformance edge cases | SDK/core owner + security reviewer | Reviewed contracts and failing acceptance fixtures for D2–D7; no alternate verifier semantics. **PROPOSED** |
| 2 / P0 — minimal offline workbench | Add guided local SDK authoring, isolated project store, safe kit export, complete language samples, shared verifier/report integration and CLI alias feasibility | Desktop + SDK owners | D1–D7 pass in source/frozen tests and candidate payload; no external toolchain required for built-in flow. **NOT IMPLEMENTED** |
| 3 / P0 — signed Windows qualification | Extend packaging/inventory, identity/coexistence, WebView2 delivery, installed lifecycle and accessibility; reuse existing record instead of resetting verifier evidence | Windows build/test owner | D1–D10 pass on exact signed candidate; retain hashes/environment/results. **NOT RUN** |
| 4 / P0 — distribution readiness | Runtime/SDK SBOM, licenses, security dispositions, release/IP review, support/privacy/listing assets, Partner Center identity, WACK and certification | Security/license + publisher/release owners | D11–D12 pass and authorized release decision. **OPEN**; no submission by this review |
| 5 / P1 — optional integrations | Authenticated loopback Dev endpoint, explicit hosted profiles, connector development tooling, richer languages/profiles | SDK/platform owners | Separate threat model and acceptance matrix; no change to offline baseline or enterprise deployment boundary. **DEFERRED** |

### Inputs still needed from the owner

- Product/SKU/name and pricing decision; supported OS/architecture commitment.
- Authorized Partner Center publisher, exact production identity and branding.
- Assigned SDK, Windows, security/license and release owners; support/privacy URLs.
- Retained signed-candidate and Lenovo/clean-client evidence (not private keys).
- Whether external SDK samples must build fully disconnected after explicitly
  documented toolchain preparation, or whether optional online restore is acceptable.

**Next engineering increment after approval:** define the kit/project/CLI contract
and a signed synthetic SDK → bundled verifier acceptance fixture before building
new UI. Continue existing Verifier WACK/evidence work independently; do not delay
or reclassify its current operator results just because Developer Edition is new.
