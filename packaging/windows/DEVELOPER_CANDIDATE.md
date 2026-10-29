# Desktop Developer preview packaging

This is an unsigned engineering candidate, not a Store-ready or production SKU.
It has the separate local identity `ETSDeveloper.Development` and executable
`ets-developer.exe`. The existing `ETSVerifier.Development` identity and
`ets-desktop.exe` defaults are unchanged. Distinct identities permit a later
coexistence test; they do not establish that signed install/lifecycle tests passed.

## Build inputs and boundaries

- Build the shared frozen verifier with `verifier.spec`, the Developer host with
  `developer.spec`, then copy the complete `dist/ets-verify` folder to
  `dist/ets-developer/verifier`. Never redistribute an isolated frozen EXE.
- `developer-kit.json` pins one already-tested alpha SDK ZIP by exact artifact,
  run, source, byte count and SHA-256. CI downloads only that artifact, then
  `stage_developer_kit.py` verifies its source and all 74 manifest members without
  extracting or running code. If the artifact expires or fails validation, stop;
  updating the pin requires a reviewed change. Do not silently fetch “latest.”
- The SDK-kit source and the Desktop candidate source are intentionally different
  immutable commits. Both are retained in the review evidence. The bundled kit
  remains alpha and has no release provenance attestation.
- The Developer package bundles Python for the built-in synthetic workflow and
  the strict verifier. WebView2 is still an external GUI runtime prerequisite.
  Exported Python, .NET/C#, TypeScript and PowerShell samples have separate,
  documented toolchain/dependency prerequisites; kit export does not install them.
- Build tools themselves require Python 3.12, PyInstaller, the pinned desktop
  requirements and Windows SDK MakeAppx. These are not end-user SDK requirements.

The workflow runs source tests, a relocated frozen verifier, native Developer UI
smoke with language tools removed from its PATH, and the same workflow under
program-scoped network blocks on a disposable Windows Server runner. Those are
engineering checks, not clean Windows 11 installation, physically disconnected
network testing or a claim that WebView2/Windows makes no background requests.

## Outputs

`windows-developer-candidate.yml` uploads:

- `ets-developer-windows-x64-unsigned-<source>`: complete portable frozen payload.
- `ets-developer-review-<source>`: unsigned `ETSDeveloper.Development_0.1.0.0_x64_unsigned.msix`,
  validated payload inventory, qualification metadata, source-bound candidate
  record and retained test evidence.
- `ets-developer-windows-results-<source>`: diagnostic evidence, including on failure.

The source suffix is the exact checkout commit (a PR merge commit for PR builds),
not necessarily the PR head. Verify the review bundle with
`python packaging/windows/candidate_record.py verify <fresh-extraction>`.
Unsigned hashes detect changes but do not authenticate a publisher.

For a local engineering build after staging the exact reviewed kit:

```powershell
./packaging/windows/build-msix.ps1 -Source dist/ets-developer `
  -OutputDirectory dist/developer-msix -PackageVersion 0.1.0.0 -Edition developer
```

No signing, trust installation, production publisher identity, registry
publication, release, deployment, Store submission, or merge is performed.

## Authorized next step: separate Developer client evidence

Use the [Developer signing, installation and WACK handoff](../../docs/commercial/WINDOWS_DEVELOPER_QUALIFICATION.md)
only after the owner authorizes those Windows actions. The helper requires explicit
`-Edition developer` and an already-approved `CN=ETSDeveloper.Development` certificate.
Verifier signing and Lenovo results are not Developer evidence. No key, trust,
installation, security/network or WACK operation is performed by this build.

## Remaining release gates

Keep WACK, clean Windows 11 standard-user installation and uninstall/upgrade,
standalone Verifier coexistence, WebView2 missing/present/update behavior, real
dialogs/Narrator/scaling, runtime and kit SBOM reconciliation, license/IP review,
support/privacy/listing accuracy, approved SKU/publisher identity, signing and
Store certification open until exact-candidate evidence and authorization exist.
The current sandbox is partial Developer functionality, not a project manager,
production signing service, hosted integration, or external code runner.
