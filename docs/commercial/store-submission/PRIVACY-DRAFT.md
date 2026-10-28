# Privacy notice — owner draft, not published

**Do not upload or publish until the owner resolves all bracketed fields and
reviews the final application and distribution.** Public privacy URL: unfilled.
No privacy/legal compliance approval is asserted by this draft.

## ETS Desktop Developer (Preview)

Publisher: [OWNER: legal publisher name]
Effective date: [OWNER: effective date]
Privacy contact: [OWNER: monitored contact address or form]

### Local files and built-in workflow

The built-in developer workflow creates a synthetic example in a folder you
choose. You can select an ETS evidence bundle and public trust material for local
verification. The application writes verification reports and a bundled SDK
archive only to destinations you select. Its temporary synthetic signing key is
not saved; the exported sample trust file contains a public test key.

The current application implements no account/sign-in flow, analytics collection
or automatic upload of selected evidence to the publisher. Core example creation,
offline verification, report export and SDK archive export do not require a
publisher-operated online service. This does not mean Windows, Microsoft Store,
WebView2 Runtime, security software or your cloud-synced folders make no network
requests. Those components and services are governed by their respective settings
and privacy terms. Choosing a synced or shared destination may expose your files
through that service; use a local folder for private/offline work.

### Information in outputs and support requests

Selected evidence and generated reports can contain information present in the
bundle you chose. Review files before sharing them. The publisher receives
support information only when you choose to send it through the support channel.
Do not send passwords, access tokens, private signing keys or customer evidence.
Use a synthetic reproduction where possible.

[OWNER: describe the approved support provider, data received, purposes, sharing,
retention period, security measures, and deletion/contact procedure. Confirm
whether Store crash analytics or other diagnostics will be received and disclose
them accurately. Do not leave this section unresolved.]

### Control and deletion

You control the exported folders and files. Delete them using your normal file
management tools when you no longer need them. Uninstalling this app does not
remove output files stored in locations you chose. Deletion from synced locations,
backups or support systems depends on those systems and their retention rules.

### Exported SDK projects

SDK export copies a bundled archive; it does not execute its source examples.
When you separately run SDK examples or connect them to an endpoint, the code,
credentials, network destinations and services you choose determine that data
flow. Read the kit documentation before using any endpoint or real data.

### Changes and contact

[OWNER: add how material notice changes are communicated and how privacy requests
are handled, including any applicable jurisdictional rights.]

## Publication checklist (remove from published notice)

- Resolve publisher/effective date/contact and support/diagnostic practices.
- Review final binary/runtime behavior and all shipped SDK contents.
- Publish at an owner-controlled public HTTPS URL without a sign-in wall.
- Verify content, reachability, accessibility and the exact Partner Center URL.
- Decide the in-app notice/link approach; any implementation needs a separately
  reviewed code change. This draft does not add an in-app privacy surface.
- Microsoft Store policy 10.5.1 requires a privacy policy for Win32/Desktop Bridge
  apps; offline operation does not remove this requirement. See
  [official policy](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies).
