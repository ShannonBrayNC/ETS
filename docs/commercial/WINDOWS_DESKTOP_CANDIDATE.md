# Windows desktop verifier candidate

Status: engineering candidate; not an MSIX or Store release.

The first desktop shell uses Python/pywebview with the Windows EdgeChromium
(WebView2) renderer. It loads only bundled HTML, with no web server or remote UI.
Microsoft Edge WebView2 Runtime must already be installed. Runtime provisioning,
MSIX dependency handling, complete dependency notices, and client OS qualification
remain release gates.

## Workflow

1. Choose an evidence bundle through the native file dialog.
2. Choose an independently obtained trust-store JSON file. Without trusted keys,
   a structurally valid bundle produces an indeterminate outcome.
3. Optionally enter an expected log ID, then select **Verify offline**.
4. Inspect the status, individual checks, checkpoint limitation, and full outcome.
5. Export the displayed result as JSON, Markdown, or HTML to a new filename.

The desktop invokes the packaged CLI in a separate process with a 30-second
timeout and no shell. It always requires a checkpoint signature; it never exposes
the CLI's development-only unsigned acceptance. Native dialogs supply file paths;
JavaScript cannot submit arbitrary read/write paths through the bridge. A cancelled
dialog preserves the prior selection. Selecting a different file or editing the
expected log ID clears the UI result and disables export until verification runs.

Reports export the saved verification snapshot rather than re-reading the source.
The snapshot includes its original verification time when available. It does not
assert that the source file is unchanged since verification. The native controller
clears its cached result on a new verification attempt or completed file selection.
Existing files are protected by the strict report writer.

All artifact strings enter the DOM through textContent. The shell has no external
assets, links, network requests, or input HTML rendering. Its content policy blocks
remote resources and connections; inline script/style and evaluation support the
bundled UI and pywebview bridge. This is an application boundary, not an OS network
sandbox. Native WebView2 runtime activity and blocked-network behavior still need
qualification.

## Build and run

Use Windows x64 and Python 3.12 from the repository root:

```powershell
python -m pip install . -r packaging/windows/requirements-build.txt
python -m PyInstaller --clean --noconfirm packaging/windows/verifier.spec
python -m pip install -r packaging/windows/requirements-desktop.txt
python -m PyInstaller --clean --noconfirm packaging/windows/desktop.spec
Copy-Item dist/ets-verify dist/ets-desktop/verifier -Recurse
./dist/ets-desktop/ets-desktop.exe
```

Keep the entire `ets-desktop` folder together, including its `verifier` subfolder.
No Python installation is required to run the frozen candidate. The desktop's
runtime dependencies are optional and are not added to the core SDK dependency
list. To run from source after installing the desktop requirements:

```powershell
python -m ets.desktop.host
```

## Validation boundaries

- Controller tests exercise the actual CLI, snapshot exports, stale-result
  invalidation, timeout handling, subprocess response validation, option injection,
  native-dialog cancellation, and protected existing files.
- Browser tests use a mocked native bridge to exercise every result class,
  exports, untrusted text rendering, result invalidation, and narrow layout.
  These tests do not establish native dialog or WebView2 behavior.
- The Windows workflow builds the host and bundled CLI and launches a native
  WebView2 smoke test. The smoke test checks that the page and bridge are ready,
  then exits; it does not simulate a complete native file-dialog workflow.

Keyboard-friendly native buttons, visible focus, live status, labelled fields,
large click targets, zoom support, and a single-column narrow layout are provided.
Manual Narrator, Windows high-DPI, standard-user clean-machine, full native-dialog,
and offline client testing remain required before beta qualification.

Remaining product gates include package identity/assets, signing, MSIX lifecycle,
trust-store onboarding, supported Windows versions, full C3 profile qualification,
and Store review. See [the readiness assessment](WINDOWS_VERIFIER_READINESS.md).

References: [pywebview API](https://pywebview.flowrl.com/api/) and
[freezing guidance](https://pywebview.flowrl.com/guide/freezing).
