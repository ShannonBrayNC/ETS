# Windows Verifier: Phase 1 Readiness

Date: 2026-10-28  
Scope: First engineering increment of the [go-to-market plan](GO_TO_MARKET_PLAN.md).

## Decision

Qualify a frozen verifier runtime before implementing the Store desktop shell.
The initial build target is Windows x64 with Python 3.12, using PyInstaller's
directory bundle. The end user runs the bundled executable without installing
Python. Keep every file in the bundle together. This is an unsigned engineering
CLI candidate, not a desktop product, installer, or Store submission.

Windows 11 x64 is the proposed first client qualification target. The CI runner
is Windows Server 2022 and does not establish Windows 11 support. ARM64 and older
Windows versions remain unqualified. A client OS support commitment requires
testing on the actual supported Windows versions.

The preferred desktop direction remains WebView2 with bundled local verification.
The current increment deliberately preserves the existing CLI and protocol
contracts so packaging failures can be isolated from new UI behavior.

## Repository assessment

| Area | Existing evidence | Consequence for release |
| --- | --- | --- |
| Verifier entry point | `ets/verifier/cli.py` exposes `ets-verify` | Reuse the public CLI for the packaging experiment |
| Strict offline checks | `ets/verifier/service.py` checks event/leaf/root bindings and signed checkpoints using out-of-band trust | Use `offline` for trust-bearing qualification; legacy `bundle` is not equivalent |
| Runtime dependencies | `pyproject.toml` includes cryptography, Pydantic, Jinja2, FastAPI, HTTPX, idna, and Starlette | Install existing constraints; assess a smaller distribution later rather than changing the SDK dependency contract here |
| Dynamic imports | `ets/core/__init__.py` lazily resolves compatibility exports | Include core submodules in the PyInstaller analysis and test the frozen executable |
| Existing UI | `ets/explorer-ui` and `apps/console/web` | Reuse requires an offline and accessibility assessment; neither is automatically a qualified desktop shell |
| Reports | `offline --report` exports freshly computed outcomes in JSON/Markdown/HTML; legacy `certificate` remains separate | Desktop should use strict report semantics and preserve policy/limitations |
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

## Remaining gates, in priority order

| Priority | Gap | Required evidence |
| --- | --- | --- |
| P0 | Windows candidate execution | Green Windows source/frozen tests and retained artifact hashes for the exact commit |
| P0 | Untrusted input boundary | CLI bounded reads, nesting/item limits, duplicate/non-finite/Unicode rejection now covered by regression tests; desktop integration and full profile/resource-policy qualification remain |
| P0 | Result and trust semantics | Strict offline CLI distinguishes invalid, unsupported, and indeterminate states and exports those outcomes with trust policy and offline limitations; desktop presentation remains |
| P0 | Offline desktop workflow | Choose/open bundle and trust inputs, verify, inspect results, export; no account or collector needed; no remote content execution |
| P0 | Actual client qualification | Windows 11 x64 standard-user clean-machine testing without Python/Git; network disabled; keyboard/Narrator/high-DPI testing |
| P0 | MSIX identity and lifecycle | Actual Partner Center identity, package manifest/assets, dependency notices, installation/update/uninstall and data-preservation evidence, WACK and Store review |
| P1 | Dependency supply chain | Reviewed lock strategy, SBOM/license inventory, vulnerability gates, signed distribution and provenance |
| P1 | Agent/enterprise delivery | Separate signed MSI, service identity and IPC authorization, durable queues, recovery and compatibility policy |
| P1 | Commercial operations | Approved pricing/quotas, support ownership, pilot criteria and service commitments |

The next implementation should connect the tested strict input/result/report
workflow to the desktop shell. Do not infer a supported
profile, accept bundle-provided trust anchors automatically, or add an unsigned
success mode to the consumer UI.

No Store identity, signing credential, price, launch date, or production approval
is fabricated by this increment. Existing release/IP gates continue to apply.

## References

- [Verifier behavior and trust store](../../ets/verifier/README.md)
- [Proposed offline verifier contract](../core/ETS_CORE_C3_OFFLINE_VERIFIER_CONTRACT.md)
- [PyInstaller usage and platform-specific builds](https://pyinstaller.org/en/stable/usage.html)
- [Microsoft distribution paths](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path)
