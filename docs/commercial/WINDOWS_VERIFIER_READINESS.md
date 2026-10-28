# Windows Verifier: Phase 1 Readiness

Date: 2026-10-28  
Scope: Engineering candidate and remaining release gates for the [go-to-market plan](GO_TO_MARKET_PLAN.md).

## Decision

The engineering candidate now includes a frozen x64 verifier, a pywebview/WebView2
desktop host, strict report export, and an unsigned development MSIX. Python 3.12
and the required application runtime are bundled with PyInstaller; WebView2 remains
an external prerequisite. Keep every file in the unpacked bundle together.

This is a tested engineering candidate, not a signed install-qualified beta or
Store submission. The separate desktop, CLI and MSIX artifacts serve different
qualification purposes.
Windows 11 x64 is the proposed first client qualification target. The CI runner
is Windows Server 2022 and does not establish Windows 11 support. ARM64 and older
Windows versions remain unqualified. A client OS support commitment requires
testing on the actual supported Windows versions.

The [first desktop candidate](WINDOWS_DESKTOP_CANDIDATE.md) implements WebView2
through pywebview, native file dialogs, the separate bundled CLI, and strict report
exports. It preserves existing protocol contracts. Windows client and MSIX release
qualification remain separate from engineering CI.

## Repository assessment

| Area | Existing evidence | Consequence for release |
| --- | --- | --- |
| Verifier entry point | `ets/verifier/cli.py` exposes `ets-verify` | Reuse the public CLI for the packaging experiment |
| Strict offline checks | `ets/verifier/service.py` checks event/leaf/root bindings and signed checkpoints using out-of-band trust | Use `offline` for trust-bearing qualification; legacy `bundle` is not equivalent |
| Runtime dependencies | `pyproject.toml` includes cryptography, Pydantic, Jinja2, FastAPI, HTTPX, idna, and Starlette | Install existing constraints; assess a smaller distribution later rather than changing the SDK dependency contract here |
| Dynamic imports | `ets/core/__init__.py` lazily resolves compatibility exports | Include core submodules in the PyInstaller analysis and test the frozen executable |
| Desktop UI | `ets/desktop/index.html`, controller and WebView2 host | Browser keyboard/failure tests and native bridge tests pass; real dialogs and Narrator remain client gates |
| Reports | `offline --report` exports freshly computed outcomes in JSON/Markdown/HTML; legacy `certificate` remains separate | Native signed-result and export tests preserve strict policy and checkpoint-only limitations |
| Proposed C3 contract | `docs/core/ETS_CORE_C3_OFFLINE_VERIFIER_CONTRACT.md` is marked proposed | CLI retains 0/1/2; strict offline adds explicit status classes and bounded JSON input, but does not implement the full proposed profile/exit-code contract |

## Implemented packaging experiment

- `packaging/windows/verifier_entry.py`: delegates to the existing CLI.
- `packaging/windows/verifier.spec`: bundles the runtime, dynamic core imports,
  project LICENSE, and NOTICE; no elevation request or collector service.
- `packaging/windows/requirements-build.txt`: pins the PyInstaller tool version.
- `.github/workflows/windows-verifier-candidate.yml`: builds on Windows x64,
  tests source and relocated executable, and uploads the unsigned runtime plus
  test results, source SHA, dependency inventory, and per-file SHA-256 hashes.
- `tests/unit/test_verifier_standalone.py`: exercises version reporting, signed
  offline verification, tampering, missing trust, untrusted keys, malformed input,
  and legacy report export against source or a configured executable.

The executable tests relocate the bundle into a path containing spaces, run
outside the checkout, clear Python lookup variables, and remove Python from the
child PATH. This checks bundling independence. It does not establish a clean
machine, standard-user token, blocked network, or Windows certification result.
The test key is a public deterministic fixture, never a deployment identity.

## Developer build and validation

Run from the repository root in a Windows x64 Python 3.12 environment:

```powershell
python -m pip install . -r packaging/windows/requirements-build.txt "pytest>=9.0.3,<10"
python -m pytest tests/unit/test_verifier_standalone.py tests/unit/test_verifier_service.py tests/unit/test_verifier_cli_golden_paths.py
python -m PyInstaller --clean --noconfirm packaging/windows/verifier.spec
$env:ETS_VERIFY_EXECUTABLE = (Resolve-Path dist/ets-verify/ets-verify.exe).Path
python -m pytest tests/unit/test_verifier_standalone.py --junitxml=test-results/windows-verifier.xml
```

Build separately on each target OS. A Linux build exercises the recipe but is
not a Windows executable or Windows qualification. Dependencies retain the
repository's version ranges: the recorded inventory aids diagnosis, but this
increment does not claim reproducible builds or a complete license/SBOM review.

## Recorded engineering evidence

These runs establish the listed behavior for their tested commits. They are not
approval for a later candidate; repeat qualification for the exact release commit
and retain artifact hashes and test results before CI artifact retention expires.

| Evidence | Recorded run | Scope and limits |
| --- | --- | --- |
| Frozen CLI, desktop and MSIX | [Windows run 40653170227](https://github.com/ShannonBrayNC/ETS/actions/runs/40653170227) | Source/frozen tests, native WebView2 workflow, MakeAppx validation and unpacked payload hashes; unsigned package on Windows Server 2022 |
| Native signed trust states | [Windows run 40651351897](https://github.com/ShannonBrayNC/ETS/actions/runs/40651351897) | Missing trust, valid signature, tampering, malformed input and exact strict report export; deterministic selections replace real dialogs |
| Program-specific network blocks | [Windows run 40653170227](https://github.com/ShannonBrayNC/ETS/actions/runs/40653170227) | Native workflow succeeds with active firewall blocks covering frozen executables and observed WebView2 paths; rules removed afterward; elevated runner, not physical isolation |
| Keyboard and connection failure | [Windows/browser run 40645061068](https://github.com/ShannonBrayNC/ETS/actions/runs/40645061068) | Browser keyboard focus, busy controls, bridge rejection and retry; mocked bridge, not Narrator certification |
| Dependency evidence | [Inventory recipe](WINDOWS_DEPENDENCY_EVIDENCE.md) | Metadata and available license files included and hashed in desktop/MSIX; unreviewed build-environment inventory, not runtime SBOM |
| Signing helper | [Signing procedure](WINDOWS_SIGNING_QUALIFICATION.md) | Existing-certificate helper and negative-path tests; successful signing and certificate-provider access have not been qualified |

## Remaining gates, in priority order

| Priority | Gate | Next action and exit evidence |
| --- | --- | --- |
| P0 | Candidate identity and signing | Record exact candidate source/package hashes; signing owner supplies approved development certificate; execute helper and retain successful signature verification; obtain exact Partner Center identity separately |
| P0 | Runtime provisioning | Qualify WebView2 installation/detection and startup on a clean Windows 11 x64 machine without developer tools; record runtime and OS versions |
| P0 | Installation lifecycle | Run signed install, launch under package identity, upgrade, downgrade rejection, removal and reinstall; retain user-file hashes and results using the [client procedure](WINDOWS_SIGNING_QUALIFICATION.md) |
| P0 | Actual client workflow | Standard-user verification with real dialogs and network disabled; validate strict statuses and exports without Python/Git/SDK; no inference from elevated Server CI |
| P0 | Accessibility | Complete keyboard, Narrator and 200% scaling checks on the actual client; record defects and retest evidence |
| P0 | Distribution obligations | Map frozen/native runtime components, resolve missing license evidence, approve notices and produce runtime SBOM/vulnerability disposition before external distribution |
| P0 | Store release | Verified publisher/package identity, approved branding, privacy/support information, WACK and Store review; existing release/IP gates remain |
| P1 | Protocol/profile coverage | Maintain bounded-input regressions and assess full proposed C3 profile/resource-policy compatibility; current CLI exit contract remains 0/1/2 |
| P1 | Reproducibility and provenance | Review dependency locking and retain candidate source, build environment, artifacts and hashes; current inventories do not prove reproducible builds |
| P1 | Agent/enterprise delivery | Separate signed MSI, service identity and IPC authorization, durable queues, recovery and compatibility policy |
| P1 | Commercial operations | Approved pricing/quotas, support ownership, pilot criteria and service commitments |

The next release step is **signed clean-client qualification**, using the
[release qualification record](WINDOWS_RELEASE_QUALIFICATION_RECORD.md) and
[signing/client procedure](WINDOWS_SIGNING_QUALIFICATION.md). Required external
inputs are an approved certificate with an authorized signing owner, a disposable
Windows 11 x64 test machine, a WebView2 provisioning decision, and assigned client
and release reviewers. None has been inferred from passing repository checks.

Until those gates are recorded as passed, retain the engineering-candidate label.
Do not infer supported profiles, accept bundle-provided trust anchors automatically,
or add an unsigned success mode. No Store identity, credential, price, launch date
or production approval is fabricated by this status update.

## References

- [Verifier behavior and trust store](../../ets/verifier/README.md)
- [Proposed offline verifier contract](../core/ETS_CORE_C3_OFFLINE_VERIFIER_CONTRACT.md)
- [PyInstaller usage and platform-specific builds](https://pyinstaller.org/en/stable/usage.html)
- [Microsoft distribution paths](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path)
