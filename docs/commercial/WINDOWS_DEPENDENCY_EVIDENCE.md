# Windows dependency evidence

The Windows candidate workflow collects installed Python distribution metadata and
available license/notice files after building the desktop and verifier. It places
`THIRD_PARTY_EVIDENCE` in the desktop artifact before staging the MSIX, so the
existing package inventory hashes these evidence files too.

For a local build, run after installing all desktop/build dependencies and building
the frozen payload, but before `build-msix.ps1`:

```powershell
python packaging/windows/collect_dependency_evidence.py --output dist/ets-desktop/THIRD_PARTY_EVIDENCE
```

Use a fresh output directory. `inventory.json` records each installed distribution's
name, version, license expression/text/classifiers, requirements, available license
file locations and copied SHA-256 hashes. Copies preserve original file bytes.
Missing license files are explicitly flagged. Every component starts `unreviewed`;
`redistributionApproved` and `completeRuntimeSbom` are always false.

This is **build-environment evidence**, including development/test tools, not a
runtime SBOM or a legal conclusion. The standalone CLI artifact does not include
this desktop evidence directory. Python distributions can include native libraries
with additional obligations, and their metadata can be absent or incomplete.

Before release, the release owner must:

1. Map the actual frozen modules and native binaries to their supplying components,
   including Python and WebView2, and distinguish tools not shipped to customers.
2. Resolve every missing license and inspect copied notices against the exact
   versions shipped. Review redistribution obligations and required attribution.
3. Produce reviewed customer-facing third-party notices and an accurate runtime
   SBOM; do not rename this environment inventory as an SBOM.
4. Review vulnerabilities for the actual shipped components and retain the scan,
   disposition, source SHA, package hash and approval together.

The collector ignores absolute/traversal paths, symlink files, and files resolving
outside the installation root. It refuses existing output directories. CI tests
byte preservation, hashes, missing evidence, path containment and no-overwrite.
An incomplete collection or legal review remains a release blocker; an inventory
file alone does not close the dependency supply-chain gate.
