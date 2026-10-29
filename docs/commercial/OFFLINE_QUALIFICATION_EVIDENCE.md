# Offline Windows qualification evidence reconciliation

This small engineering-workstation utility assembles **supplied files only**.
It does not contact GitHub, inspect a Windows device, sign anything, access keys,
install software/certificates, change trust/network settings, run WACK, or approve
a release. Python 3.12 is needed on the engineering workstation, not the clean
Windows client. It executes no programs from a review bundle.

## Start with the existing reviewed unsigned bundle

Select the exact source commit and run independently from retained review evidence.
Do not replace those values with whatever an unreviewed JSON file happens to say.
For the retained Developer PR #953 candidate, the packaged source is
`84ef3036f9770df462b5ac805b014c2f522b1437`, not its PR head or later main merge.

```powershell
python packaging/windows/qualification_evidence.py `
  --review '<unchanged extracted Developer review bundle>' `
  --edition developer `
  --source-sha 84ef3036f9770df462b5ac805b014c2f522b1437 `
  --run-url https://github.com/ShannonBrayNC/ETS/actions/runs/40785794103 `
  --output '<new evidence directory outside the review bundle>'
```

For Verifier, explicitly select `--edition verifier` and its actual source/run.
The tool reuses `candidate.json` validation, checks every reviewed MSIX payload
hash, manifest identity/publisher/x64/version, and packaging qualification fields.
Wrong edition, source, run, hashes, ambiguous paths or mismatched records fail closed.
Existing output is protected. Inputs are never edited. Inputs are bounded to
4,096 files, 512 MiB per file, 1 GiB total, and 64 MiB per WACK attachment.
Hashes are pinned before validation; copied records and payloads are revalidated
before a success record is written.

## Add evidence only after separately authorized operator work

The following optional arguments consume existing files; they do not cause the
underlying Windows actions:

- `--signed-package '<signed MSIX>' --signing-record '<signing.json>'`: a required
  pair when either is supplied. Signed and unsigned manifest/payload bytes must
  agree, and both recorded digests, edition, version and public thumbprint fields
  must be coherent. Uses the edition-aware signing-record fields from #953;
  unsupported legacy records stop for review, not silent backfilling.
- `--client-preflight '<client-preflight.json>'`: bind the supplied observations
  to the signed digest; reject a conflicting public signer thumbprint. Negative
  observations can be retained. A reported `Valid` signature is not reverified.
- `--installed-package '<installed-package.json>'`: check the supplied name,
  publisher, version, architecture and full-name prefix/shape consistency. The
  publisher-ID suffix is retained but not independently derived. Metadata does not
  prove which bytes were installed, or that installation or startup succeeded.
- `--wack-xml '<wack.xml>' --wack-html '<wack.html>'`: retain and hash the supplied
  reports as opaque files. Either may be absent. Their contents, authenticity,
  success and binding to this package are **not** established by this utility.

Client/installed/WACK evidence requires the corresponding signed pair. Follow
[the Developer handoff](WINDOWS_DEVELOPER_QUALIFICATION.md) or
[Verifier qualification](WINDOWS_SIGNING_QUALIFICATION.md) for separately authorized
operator work. Never put private keys, passwords or customer evidence in this bundle.

## Interpret the output conservatively

`qualification-evidence.json` contains source/run, edition, package digests and
copied-file hashes; `QUALIFICATION.md` is a factual review summary. Original records
and supplied reports are retained alongside them. `integrityVerified: true` means
file/record consistency only. It is **not** authenticated origin or a verified
signature: even structurally present signature bytes are not cryptographic proof.

All owner/manual gates remain **NOT RUN by this assembler**, including signing,
clean-client behavior, lifecycle, accessibility, WACK and Store certification.
`clientQualified`, `wackPassed` and `releaseApproved` remain false, even when an
attachment says PASS. Prior operator claims must be reviewed separately; the tool
neither promotes them to verified success nor declares that they never occurred.
No signer, tester, license reviewer or approver is inferred.

A mismatch exits nonzero. A failed or interrupted output is diagnostic only;
retry into a fresh directory. Keep the original immutable review bundle. Use the
existing [qualification record](WINDOWS_RELEASE_QUALIFICATION_RECORD.md) to record
actual reviewers, observed tests and authorized decisions—not another owner worksheet.
