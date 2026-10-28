# Unsigned development MSIX candidate

This increment wraps the frozen desktop and verifier in an MSIX with the explicit
development identity `ETSVerifier.Development` and publisher
`CN=ETSVerifier.Development`. These are engineering values, not Partner Center
identifiers. The package is unsigned and is not install-qualified or Store-ready.

## Build

On Windows with PowerShell 7, Python 3.12, and the Windows SDK installed, build
the [desktop candidate](WINDOWS_DESKTOP_CANDIDATE.md), then run from the repo root:

```powershell
./packaging/windows/build-msix.ps1 -PackageVersion 0.1.0.0
```

Use a fresh output directory for each run; the script refuses to overwrite one.
`-Source`, `-OutputDirectory`, and `-MakeAppxPath` can override defaults. The script
selects the newest installed x64 MakeAppx from versioned Windows SDK directories.
The package version must have four components, each at most 65535, with final
component zero. The development layout builder does not accept Store identity
overrides; adopting a verified production identity is a separate reviewed change.

## What is checked

- Both launch executables have x64 PE headers and the bundled HTML exists.
- The copied payload contains no symlinks and the layout is outside the source.
- The manifest declares a desktop full-trust application, not administrator
  elevation, with only the `runFullTrust` restricted capability.
- Deterministic engineering PNG tiles satisfy the referenced asset dimensions.
- MakeAppx validates the manifest and package during packing; validation is not
  bypassed with `/nv`.
- MakeAppx unpacks the generated package and every staged file is checked against
  its original SHA-256 digest, including the manifest and assets.

The artifact includes the unsigned MSIX, `layout-sha256.json`, and
`qualification.json` with package hash, identity, version, tool path, UTC build
time, and explicit signing/installation status. Layout and unpacked working
directories remain local build outputs and are not included in the CI download.

The manifest sets a Windows 11 compatibility floor (`10.0.22000.0`). Its version
fields are configuration values, not evidence of client OS testing. Windows Server
CI proves packaging and unpacked host startup only. WebView2 Runtime is still an
external prerequisite and is not provisioned by this package.

See [development signing and client qualification](WINDOWS_SIGNING_QUALIFICATION.md)
for the existing-certificate helper and the install/update/removal evidence matrix.
Successful signing and client lifecycle tests remain unexecuted release gates.

The CI desktop and MSIX also contain [dependency license evidence](WINDOWS_DEPENDENCY_EVIDENCE.md).
This is an unreviewed build-environment inventory, not a complete runtime SBOM.

## Remaining release gates

1. Obtain exact Partner Center package/publisher identity and approved branding.
2. Review all runtime licenses, notices, dependency inventory, and signing process.
3. Qualify WebView2 provisioning and startup without developer tools.
4. Sign a test candidate through an approved process and test installation,
   launch under package identity, upgrade, removal, and data preservation on a
   clean Windows 11 standard-user machine.
5. Complete native file-dialog workflows, network-disabled verification, Narrator,
   keyboard navigation, high-DPI, WACK, and Store certification.

No signing credential is generated or committed. No package is submitted to the
Store. The package must not be described as installed or certified based solely
on MakeAppx success.

References: [Microsoft package components](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion)
and [MakeAppx](https://learn.microsoft.com/en-us/windows/uwp/packaging/create-app-package-with-makeappx-tool).

## Self-contained reviewer handoff

CI also publishes `ets-verifier-review-<source SHA>`. It contains the unsigned
MSIX, packaging metadata, this Windows job's test results, and `candidate.json`.
The record identifies the exact checked-out Git commit (a synthetic merge commit
for PR runs), workflow URL, relative filenames, sizes and SHA-256 hashes. It omits
MakeAppx working trees. Archive this artifact before CI retention expires.

After downloading and extracting to a fresh directory, check it with Python 3.12
and the script from the reviewed repository commit:

```powershell
python packaging/windows/candidate_record.py verify ./extracted-review
```

Verification rejects changed/missing/extra files, unsafe paths, symlinks and
Windows reparse points (including junctions) before traversing their contents.
It also rejects duplicate JSON fields, invalid metadata/file records and approval
flags inconsistent with an unsigned engineering record.
Assembly refuses existing output and verifies the package against its qualification
hash. A failed assembly directory must not be used as a qualified handoff.

This record is unsigned. Hash verification detects changes relative to the record;
it cannot authenticate the record, its claimed source, or the build origin. Obtain
it from the expected repository/run and independently review that source. It is not
an attestation, reproducible-build proof, complete CI summary or release approval.
Browser/other-job results and signed Windows 11 client evidence must be retained
separately. Use the release qualification record to track those remaining gates.
