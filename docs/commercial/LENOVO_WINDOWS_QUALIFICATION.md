# Lenovo Windows qualification — 0.1.1.0

This development MSIX advances the package version from 0.1.0.0 to 0.1.1.0 while retaining ETSVerifier.Development / CN=ETSVerifier.Development / x64. It includes the startup diagnostics correction. Application semantic version is unchanged; this is a packaging qualification increment.

CI builds and validates the unsigned MSIX. Sign the reviewed package on the original signing workstation with the same non-exportable certificate used for 0.1.0.0, using sign-development-msix.ps1 and the retained reviewed SHA-256. Do not copy the private key to the laptop.

Transfer the signed MSIX, signing.json, and public .cer to the Lenovo. Confirm the signed digest matches signing.json before installation. Import only the reviewed public certificate into LocalMachine/TrustedPeople with administrator assistance. Run installation and application tests as a standard user. WebView2 must be present; document any runtime provisioning.

For a fresh install, install 0.1.1.0 and launch from Start. For upgrade qualification, first install the previously signed 0.1.0.0 and verify a fixture, then install 0.1.1.0 over it. A laptop that only receives 0.1.1.0 tests fresh installation, not upgrade.

Record OS/build, architecture, elevation, WebView2 version, exact signed hashes and certificate thumbprint. Verify the golden and real Edge bundles with their separately supplied public trust files. Missing trust must remain indeterminate. Test malformed and tampered evidence, expected-log mismatch, report exports, cancellation, no-overwrite, keyboard/Narrator and 200% scaling.

Hash external fixture/trust/report files before upgrade and uninstall. Confirm their bytes remain unchanged afterward. Attempt ordinary downgrade to 0.1.0.0 without force flags and retain the rejection. Uninstall the exact development package, reinstall 0.1.1.0, and repeat verification. No step automatically establishes Store approval. If the Lenovo already contains developer tools, record that rather than calling it a clean client.

## Operator results — 2026-10-28

Operator: Shannon Bray. Device: Lenovo laptop. Package: development x64 MSIX
0.1.1.0 from Windows candidate run 40754893050 (packaged source
`ed854b4c99a0ff81745bd5590848f54c04aeb3d7`). The signing key remained on the
original workstation; the public certificate and signed installer were transferred.

| Test | Result and evidence |
| --- | --- |
| Fresh install and launch | PASS, operator report; installer screenshot shows 0.1.1.0 and subsequent application screenshot shows successful verification |
| Golden signed fixture | PASS, screenshot shows all nine checks passing with native-signed.json and native-trust.json |
| Disconnected-network operation and report export | PASS, explicit operator confirmation |
| Uninstall/reinstall and verification | PASS, explicit operator confirmation |
| External exported report retained after uninstall | PASS, explicit operator confirmation; no before/after byte hashes supplied |
| Upgrade 0.1.0.0 to 0.1.1.0 | PASS, operator confirmed the prescribed test sequence |
| Ordinary downgrade rejection | PASS, operator confirmed the prescribed test sequence |
| Keyboard navigation | PASS, operator confirmed selection, verification, outcome navigation, export and cancellation sequence |
| Narrator | PASS, operator confirmed the prescribed screen-reader sequence |
| 200% display scale | PASS, operator confirmed verification/export and window-size sequence |

These are operator-attested results, not automated logs or formal accessibility
certification. The screenshots and confirmations are retained in the testing
conversation, not committed to git. Exact Lenovo OS build, architecture report,
WebView2 version, elevation state, signed 0.1.1.0 digest and clean-machine/tool
inventory have not yet been attached. Do not describe this as a clean-VM pass.
External input/trust byte preservation is not independently established by the
report-preservation confirmation. Real Edge-bundle verification passed earlier on
the original workstation; the Lenovo screenshot demonstrates the golden fixture.

Next: [WACK handoff](WINDOWS_WACK_HANDOFF.md), then Partner Center production
identity, listing/assets, runtime/license review and production-candidate retest.
Store readiness and release approval remain false.
