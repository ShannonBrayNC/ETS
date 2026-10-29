# Desktop Developer: partial offline candidate

Current system-DPI repair and newly versioned development-candidate handoff: [Windows DPI candidate](WINDOWS_DPI_CANDIDATE.md). Prior results below remain attached to their original package bytes.

This increment implements one bounded vertical slice, not the entire Developer
Edition readiness plan. It is an **unsigned alpha engineering candidate**, not a
Store submission or release approval. The existing standalone ETS Verifier and
its Lenovo 0.1.1.0 qualification are unchanged.

## Included

- A separate `ets-developer.exe` / `ETSDeveloper.Development` engineering identity
  and MSIX version `0.1.0.0`, with the same frozen strict `ets-verify` core.
- A guided synthetic manufacturing example: create validated evidence through
  the local Python SDK, append to an in-memory log, sign a checkpoint with a new
  ephemeral sample key, and write exact bundle bytes and separate public sample
  trust. The key is not saved; no global trust is changed.
- Verification is a separate explicit step through the included CLI. Creating
  evidence does not report verification success. Initial sample trust is empty;
  the user explicitly chooses the synthetic key to demonstrate checkpoint trust.
- JSON, Markdown and HTML report export through the existing strict report
  implementation. Exports preserve existing files and reflect the displayed
  outcome, not a cached authoring success flag.
- Export of the already-tested SDK PR #951 ZIP without downloading, extracting,
  executing or installing it at runtime. Complete archive SHA-256 is checked
  before writing a new user-selected filename. The build checks all 74 manifest
  files before embedding the ZIP. An expired/missing upstream artifact fails the
  build rather than substituting a newer kit.

### Exact SDK kit dependency

| Field | Pinned value |
| --- | --- |
| SDK PR head | `d8e352923b04dc2d812399f50889ddbf21ce8a0b` |
| SDK packaged PR-merge source | `a6eb2c70b4e84cdae5f6d88e788d2fb1f663fa3e` |
| Actions run / artifact | `40772676393` / `12853576745` |
| ZIP bytes | `2034146` |
| ZIP SHA-256 | `c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7` |
| Python package | `lanternprotocol-ets 0.1.0a1` |
| C# package | `LanternProtocol.ETS.Application 0.1.0-alpha.1` |
| TypeScript package | `@lanternprotocol/ets-sdk 0.1.0-alpha.1` |

This ZIP remains an alpha test kit; PR packaging does not provide a signed
release-provenance attestation. Its SDK source is intentionally different from
the new Desktop candidate source. Both are recorded, not conflated. PowerShell
7 examples use REST/CLI; no native PowerShell SDK module is claimed.

## Test the candidate without changing the Lenovo install

1. Download the exact-source **portable Developer preview** artifact identified
   in this PR's Windows Developer candidate run. Extract the whole folder into a
   new directory, not over the existing Verifier. Keep `verifier/` and
   `_internal/` beside `ets-developer.exe`; do not copy out just an EXE.
2. On a Windows 11 x64 test client with WebView2 already provisioned, launch
   `ets-developer.exe`. This unsigned engineering package may be blocked by local
   policy; stop and obtain the release owner's authorized signing/qualification
   procedure rather than bypassing security or installing arbitrary trust.
3. Choose **Create synthetic sample…**, select a writable parent folder, and note
   the fresh `ETS-synthetic-*` child. Existing files are not replaced. A completed
   folder has `sample-summary.json` with hashes of its six preceding files.
4. Click **Verify offline** before choosing trust: expect **indeterminate**.
5. Click **Use this sample's trust**, read its synthetic-only warning, then verify:
   expect **Verified at checkpoint**, `signature_verified=true`,
   `continuity_verified=false`, and `standing_status=checkpoint_only`.
6. Export JSON/Markdown/HTML to new paths. Retry an existing filename: it must be
   protected. JSON must preserve the displayed result and strict signature policy.
7. Select the created `tampered-bundle.json`; this clears prior sample trust.
   Explicitly choose that folder's `sample-trust.json` and verify: expect
   **invalid**. A wrong expected log also fails. Selecting new material clears old
   reports. Cancelling a picker preserves the previous selection/result.
8. Click **Export SDK test kit…** and use a new ZIP filename. Compare its SHA-256
   with the table above. A second export to the same filename must not overwrite.
   Read the extracted kit's `README.md` and `docs/sdk/TEST_KIT.md` for language
   samples. These are a separate developer action, not part of GUI startup.
9. Repeat the built-in create/verify/report/kit-export flow with internet
   disconnected. Record exact candidate source/hash, OS, WebView2 version,
   standard-user/elevation status, and observed result; do not infer clean-client
   qualification from hosted Windows Server CI.

Built-in authoring/verification/export needs no user-installed Python, Node,
.NET SDK, Git, Docker or account. **The GUI still requires WebView2**; the frozen
CLI does not. External source examples require the relevant Python 3.12+,
.NET 8 SDK, Node 22.14+ or PowerShell 7 toolchain. Not all dependencies are
vendored; package restore may require network access. No global install occurs.

The SDK ZIP and created folders belong to the user. Uninstalling the app does
not remove them. Interrupted creation can leave a new partial child without
`sample-summary.json`; it does not change the previous selection or existing
evidence. Retry creates another child. A failed ZIP write may leave a partial new
file; compare its hash and retry with a fresh name. There is no project migration
or automatic cleanup of user folders in this increment.

## Verification scope and known omissions

Source tests exercise actual SDK-to-CLI serialization, missing/selected trust,
wrong log/tampering, all report formats, cancel/failure state, unique ephemeral
keys, no-overwrite, linked-folder rejection, incomplete creation and corrupt SDK
rejection. Browser tests cover controls, repeated actions, stale results, error
recovery, escaping, keyboard operation and narrow layouts. Native CI exercises
the frozen host, sample flow, report and exact ZIP export with toolchain PATH
removed and program network blocks. CI checks MSIX pack/unpack and payload
hashes; it does not install or sign the package.

There is no arbitrary evidence editor/importer, saved private-key custody,
project manager, migration, remote connection, live collector, source editor,
execution alias or independently implemented C#/TypeScript offline verifier.
Only a fixed bounded synthetic sample is authored. The core verifies bundle
integrity and checkpoint signatures, not the separately exported artifact's
bytes, physical facts, completeness, current log standing or legal sufficiency.

Still required before release:

- Authorized product/SKU/pricing/publisher identity and support/privacy decisions.
- Exact signed package clean Windows client installation/coexistence/lifecycle,
  native dialogs, keyboard/Narrator/200% scaling and interruption tests.
- WebView2 absent/present/update and offline provisioning strategy qualification.
- Full payload/SDK SBOM reconciliation, redistribution/license sign-off and
  dependency/security servicing disposition. Build inventory is not legal approval.
- WACK on the intended signed client candidate, production identity validation,
  Store certification, and release/IP approvals. No such gate is claimed here.

Continue the existing [Windows release gaps](MICROSOFT_STORE_RELEASE_GAPS.md),
[Lenovo qualification](LENOVO_WINDOWS_QUALIFICATION.md) and
[SDK release matrix](../sdk/RELEASE_MATRIX.json). The broader readiness proposal
in draft PR #950 remains a plan; this document records only this increment.
