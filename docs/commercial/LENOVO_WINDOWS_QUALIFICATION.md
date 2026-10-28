# Lenovo Windows qualification — 0.1.1.0

This development MSIX advances the package version from 0.1.0.0 to 0.1.1.0 while retaining ETSVerifier.Development / CN=ETSVerifier.Development / x64. It includes the startup diagnostics correction. Application semantic version is unchanged; this is a packaging qualification increment.

CI builds and validates the unsigned MSIX. Sign the reviewed package on the original signing workstation with the same non-exportable certificate used for 0.1.0.0, using sign-development-msix.ps1 and the retained reviewed SHA-256. Do not copy the private key to the laptop.

Transfer the signed MSIX, signing.json, and public .cer to the Lenovo. Confirm the signed digest matches signing.json before installation. Import only the reviewed public certificate into LocalMachine/TrustedPeople with administrator assistance. Run installation and application tests as a standard user. WebView2 must be present; document any runtime provisioning.

For a fresh install, install 0.1.1.0 and launch from Start. For upgrade qualification, first install the previously signed 0.1.0.0 and verify a fixture, then install 0.1.1.0 over it. A laptop that only receives 0.1.1.0 tests fresh installation, not upgrade.

Record OS/build, architecture, elevation, WebView2 version, exact signed hashes and certificate thumbprint. Verify the golden and real Edge bundles with their separately supplied public trust files. Missing trust must remain indeterminate. Test malformed and tampered evidence, expected-log mismatch, report exports, cancellation, no-overwrite, keyboard/Narrator and 200% scaling.

Hash external fixture/trust/report files before upgrade and uninstall. Confirm their bytes remain unchanged afterward. Attempt ordinary downgrade to 0.1.0.0 without force flags and retain the rejection. Uninstall the exact development package, reinstall 0.1.1.0, and repeat verification. No step automatically establishes Store approval. If the Lenovo already contains developer tools, record that rather than calling it a clean client.
