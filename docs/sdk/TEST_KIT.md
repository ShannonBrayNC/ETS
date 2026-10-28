# SDK test kit: installation and tonight's acceptance run

Scope: downloadable **alpha test packages**, documentation and synthetic examples.
No registry publishing, Store submission, production deployment or new Developer
Edition authoring UI is implied. Use the existing installed signed Desktop Verifier
for bundle inspection; keep its Windows/signing qualification separate.

## Contents and integrity

The kit contains the Python wheel and sdist, .NET Application `.nupkg` and symbols,
npm `.tgz`, SDK release manifest/SPDX SBOM/checksums, these guides, Python/C#/TypeScript quickstarts and PowerShell REST/CLI
examples, ten industry recipes, public verifier fixtures/conformance vectors,
LICENSE and NOTICE. It does not include Python, Node, .NET SDK, Docker, WebView2,
private signing keys or customer data.

Check the delivered outer ZIP SHA-256 and `test-kit-manifest.json` file hashes
against the trusted handoff. The retained `sdk-release-manifest.json` identifies
the exact CI source commit (a synthetic merge SHA for PR builds); it need not equal
the PR head. The manifest/checksums detect changed bytes, not authorship by
themselves. PR candidate builds intentionally skip release provenance attestation.
Read actual CI results; archive existence is not installed-package usability.
Candidate snapshots may share the same alpha version: identify them by source
commit and artifact hashes, and never mix cached same-version packages from
different candidates.

## Prerequisites and safe installation

Use a new test directory and isolated environments. Supported source targets are
Python 3.12+, .NET 8 SDK, Node 22.14+ and PowerShell 7 for its examples; record the exact tested versions.
Package restore requires internet for dependencies unless you have separately
prepared a complete reviewed cache/feed. The kit is not a complete offline
compiler/toolchain or dependency wheelhouse.

### Python (PowerShell)

From the extracted kit root, create a virtual environment and install the wheel:

```powershell
py -3.12 -m venv .venv
$python = Join-Path $PWD '.venv\Scripts\python.exe'
$wheel = (Get-ChildItem ./packages/python/*.whl | Select-Object -First 1).FullName
& $python -m pip install $wheel
& $python -c 'from ets.version import __version__; print(__version__)'
& $python examples/sdk/python/offline_roundtrip.py --industry manufacturing --output ./qa-example
```

Do not run `pip install ets`: that distribution name is unrelated. Expected package
version is defined by [RELEASE_MATRIX.json](RELEASE_MATRIX.json), currently
`lanternprotocol-ets` `0.1.0a1`. On macOS/Linux use your Python 3.12+ and `.venv/bin/python`.

### .NET and TypeScript

Follow [DOTNET_CLIENT.md](DOTNET_CLIENT.md) and
[TYPESCRIPT_CLIENT.md](TYPESCRIPT_CLIENT.md) using the kit's local `.nupkg`/`.tgz`,
not an assumed public registry release. The quickstarts include synthetic smoke
and explicit real-test-endpoint modes. Their `GetBundleAsync`/`getBundle` result is
unverified until passed to the common strict verifier. Never reuse smoke trust for
real data. Start with smoke; no token or live service is needed for it.

### PowerShell 7

Use [POWERSHELL_INTEGRATION.md](POWERSHELL_INTEGRATION.md) for REST capture,
retrieval, export and strict CLI invocation. This is integration code, not a
separate ETS PowerShell module. Begin with its deterministic smoke mode, then
explicitly configure an authorized test endpoint only if needed.

## Desktop handoff

Keep the signed Lenovo development Verifier **0.1.1.0** already installed if it
is the reviewed candidate. Open the Python example's `bundle.json`, choose its
`sample-trust.json` separately, enter `ets-synthetic-sdk-example`, and verify.
Expected outcome is valid at the supplied sample checkpoint, not issuer authenticity
or physical truth. The tampered bundle must fail; missing trust must not become valid.
Export JSON/Markdown/HTML under new names and compare the conclusions.

The matching Windows candidate is
[run 40754893050](https://github.com/ShannonBrayNC/ETS/actions/runs/40754893050),
review artifact `ets-verifier-review-ed854b4c99a0ff81745bd5590848f54c04aeb3d7`.
That CI artifact is **unsigned**; it is not a replacement for the signed package
already tested. If reinstalling from it, follow the approved
[signing/client procedure](../commercial/WINDOWS_SIGNING_QUALIFICATION.md) with
retained unsigned/signed hashes and the authorized owner. Do not send private keys
or passwords in chat or import a new certificate just because it arrived with a ZIP.
See [Lenovo evidence](../commercial/LENOVO_WINDOWS_QUALIFICATION.md) for actual scope.

No desktop rebuild is required solely for these SDK docs/sample/packaging changes.
This kit does **not** add the proposed Developer Edition project-authoring UI.
The desktop GUI requires provisioned WebView2; the standalone frozen verifier does
not. Windows client/WACK/Store gates remain separate from Linux SDK CI.

## Record results before calling a package ready

| Check | Expected result |
| --- | --- |
| Kit hashes/source/version inventory | All retained bytes match; exact runtime/SDK versions recorded |
| Fresh Python wheel consumer outside checkout | Actual installed `ets` imports; signed/tampered/missing-trust reports match expected outcomes |
| Fresh .NET `.nupkg` consumer | Package restore, compilation and synthetic transport flow pass; exported bundle verifies through common CLI |
| Fresh npm `.tgz` consumer | Package-name import and advertised declarations resolve; smoke flow passes; exported bundle verifies through common CLI |
| Industry recipes | All ten signed/negative/missing-trust cases behave identically at the shared verifier boundary |
| Existing outputs | Repeated export refuses overwrite; sample private key is not saved |
| Desktop manual round trip | Correct strict results and reports with selected sample trust; no unsigned-policy shortcut |
| Actual authorized test endpoint | Explicit compatibility/auth/capture/retrieve/reconciliation tested separately; record NOT RUN if not tested |

The public deterministic smoke fixtures are known test identities. A successful
mock-transport smoke is not a live-service, throughput, concurrency, trust-custody
or tenant-isolation qualification. Current conformance corpus covers limited
vectors. Successful Store checks or SDK tests do not prove production trust,
regulatory compliance, source completeness or real-world truth.
