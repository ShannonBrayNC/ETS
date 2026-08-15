# IPQ-G Integrated Evidence-Pack Audit Result

Parent: #324  
Execution sprint: #365  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Preliminary retained audit

Workflow: `IPQ-G Integrated Evidence Pack`  
Run: `31866911916`  
Harness head audited: `a284eb6525f09c32a2c28c549fa8baf47d37cee4`

Result: **PASS — retained evidence disclosure audit**

The workflow successfully downloaded the retained A-F qualification artifacts from their exact source run IDs, verified the GitHub-provided artifact digests during download, inventoried the extracted files, and scanned text evidence for high-risk secret-shaped material without echoing any matched value.

- evidence files scanned: **82**
- high-risk secret-shape findings: **0**
- integrated evidence-pack artifact ID: `9242285465`
- integrated evidence-pack ZIP SHA-256: `dcd54acad24df5c3824f661b7e51bea8e3cd1fa5074cd3197014fda618f95f02`
- uploaded files in integrated pack: 90

The scanner checks for high-risk shapes including private-key PEM blocks, bearer-token forms, AWS access-key IDs, Azure Storage account keys, and client-secret assignments. Synthetic fixture markers are counted separately and are not automatically treated as production credentials.

## Interpretation

This PASS means the retained qualification evidence pack did not expose a detected reusable credential/private-key/token shape under the implemented audit. It does **not** mean the frozen product has no credential-security defect.

IPQ-B independently proves that the frozen Edge implementation stores its reusable local API key itself in a mode-0600 file. That product behavior remains a frozen FAIL and a provisional IPQ-G no-go trigger. The evidence-pack audit and the product credential-at-rest finding are different boundaries.

## Finalization rule

This is preliminary G evidence because adding this result record changes the G branch head and because A/B/C still require final synchronization/merge. Before the final decision is merged:

1. A/B/C result branches must be finalized;
2. IPQ-G must be synchronized to then-current `main`;
3. this audit must rerun on the exact final G head;
4. CI, Security Audit, CodeQL, Formal Specs, Benchmarks, Apalache and Lean must all pass on that same head;
5. LanternProtocol must independently approve the exact final decision record.

No later result may rewrite the frozen B/D failures by importing #334 or #342 into the frozen SUT.
