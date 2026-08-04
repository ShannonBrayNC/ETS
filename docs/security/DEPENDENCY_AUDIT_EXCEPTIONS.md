# Dependency Audit Exceptions

Dependency-audit exceptions are temporary, narrowly scoped release controls. An exception does not declare a vulnerability harmless. It records why a specific advisory is not reachable in the current ETS implementation, identifies the compensating controls, and defines the condition for removing the exception.

## CVE-2026-69247 — `cryptography`

- **Status:** Temporary exception
- **Recorded:** 2026-08-04
- **Affected package:** `cryptography`
- **ETS constraint:** `cryptography>=49.0.0,<50`
- **Fixed version reported by the advisory:** `50.0.0`
- **Stable fixed release availability:** Not yet available when this exception was recorded

### Applicability assessment

The advisory affects the `pkcs7_decrypt_der`, `pkcs7_decrypt_pem`, and `pkcs7_decrypt_smime` APIs when an application decrypts attacker-controlled PKCS#7 `EnvelopedData` and exposes distinguishable outcomes.

ETS does not invoke those APIs and does not provide PKCS#7 or S/MIME envelope decryption. The current `cryptography` usage is limited to:

- Ed25519 tree-head signing and signature verification;
- RSA PKCS#1 v1.5 signature generation and verification for JWT/JWKS authentication;
- cryptographic hash primitives used by those signature workflows.

The vulnerable decryption path is therefore not reachable through the current ETS API, CLI, verifier, or report-generation surfaces.

### Compensating controls

- The minimum supported version is raised from `48.0.1` to `49.0.0`, which resolves the other current `cryptography` advisories detected by `pip-audit`.
- CI continues to run `pip-audit` and ignores only `CVE-2026-69247`.
- All tests, static analysis, formal checks, and release-readiness gates remain required.
- Adding PKCS#7, CMS, or S/MIME decryption is prohibited while this exception is active unless the exception is removed first.

### Removal criteria

Remove the CI exception and update the dependency constraint when either condition occurs:

1. A stable `cryptography` release containing the fix for CVE-2026-69247 is available and passes the ETS validation suite.
2. ETS introduces any PKCS#7, CMS, S/MIME, or attacker-controlled envelope-decryption capability.

The exception must not be broadened to other advisories without a separate documented applicability assessment.
