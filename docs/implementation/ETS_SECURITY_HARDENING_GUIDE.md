# ETS Security Hardening Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: security engineers, platform owners, DevSecOps teams, architects, and operators

## 1. Purpose

This guide explains how to harden an ETS deployment as it moves from local alpha demo toward controlled validation environments. ETS is a verification and evidence-routing layer, so the security posture must be stronger than a normal demo API. A weak ETS deployment can accidentally become a false lantern: it may appear to verify evidence while leaking secrets, mixing tenants, overclaiming certificates, or allowing forged proof material.

This guide is grounded in public-safe ETS boundaries and general secure-development guidance such as NIST SSDF, OWASP ASVS, GitHub secret protection, and Zero Trust-style controls. It does not replace a formal security assessment, certification process, penetration test, or legal review.

## 2. Non-negotiable security boundaries

ETS must not publicly store or publish:

```text
secrets
API tokens
private signing keys
real PII
real PHI/ePHI
production customer evidence
official election data
legal records
medical records
financial account records
restricted incident response details
USPTO receipts
application numbers
claim charts
attorney-review material
```

For production-like validation, ETS should default to storing metadata and hashes, not raw artifacts.

## 3. Threat model summary

| Threat | Example | Required control |
|---|---|---|
| Secret leakage | A contributor commits an API key in a fixture. | Secret scanning, push protection, PR templates, local scanning. |
| Tenant data bleed | Tenant A can fetch Tenant B events. | Tenant/workspace scoping, auth claims, negative tests. |
| Forged evidence | Caller submits misleading metadata. | Source authorization, source identifiers, signatures where applicable, policy review. |
| Tampered proof | Root hash or audit path changed. | Verifier recomputes proof path and rejects mismatch. |
| Rollback/fork suspicion | Older or conflicting tree head presented. | Consistency checks, signed tree heads, external witnessing/anchoring. |
| Overclaiming | Certificate implies election correctness or legal sufficiency. | Claim-boundary templates and certificate tests. |
| Key compromise | Tree-head signing key leaked. | Key rotation, key IDs, offline storage, revocation playbooks. |
| Public manifest poisoning | Unreviewed artifact appears in a public manifest. | Human review and release policy gate. |

## 4. Hardening phases

### Phase 0: local-only alpha

Use for developer demos only.

```powershell
$env:ETS_STORAGE_PROVIDER = "memory"
$env:ETS_AUTH_MODE = "local_header"
$env:ETS_SIGNING_MODE = "local_unsigned"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Allowed claims:

```text
Local ETS demo verifies submitted-event metadata and proof material generated in the local process.
```

Do not claim production trust, external witnessing, official custody, legal sufficiency, election correctness, or completeness.

### Phase 1: local durable validation

Use SQLite for repeatable smoke tests.

```powershell
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets-validation.db"
$env:ETS_REDACTION_PROFILE = "basic_pii"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

Controls:

```text
[ ] synthetic data only
[ ] database path excluded from git
[ ] repeatable backup/restore check
[ ] tamper tests pass
[ ] tenant/workspace negative tests pass
```

### Phase 2: controlled team validation

Use authenticated local API or JWT/JWKS. Use a non-public environment.

```powershell
$env:ETS_AUTH_MODE = "local_api_key"
$env:ETS_LOCAL_API_KEY = "replace-with-16-plus-character-local-key"
```

For JWT/JWKS validation:

```powershell
$env:ETS_AUTH_MODE = "production_jwks"
$env:ETS_AUTH_JWKS_URL = "https://issuer.example/.well-known/jwks.json"
$env:ETS_AUTH_ISSUER = "https://issuer.example/"
$env:ETS_AUTH_AUDIENCE = "ets-api"
```

Controls:

```text
[ ] no anonymous API access
[ ] tenant_id/workspace_id claims enforced
[ ] write endpoints require authorized source roles
[ ] public release routes require reviewer role
[ ] failed auth is logged without leaking token contents
```

### Phase 3: signed tree-head validation

Unsigned tree heads are acceptable for local demos, but stronger deployments need signing.

```powershell
$env:ETS_SIGNING_MODE = "ed25519"
$env:ETS_SIGNING_PRIVATE_KEY_HEX = "<32-byte-ed25519-private-key-hex>"
$env:ETS_SIGNING_PUBLIC_KEY_ID = "ets-validation-key-2026-01"
```

Controls:

```text
[ ] private key never committed
[ ] public key id appears in tree-head record
[ ] verifier records signing algorithm and key id
[ ] rotation plan exists
[ ] compromised-key playbook exists
```

### Phase 4: public verifier / public manifest validation

Use only after publication policy exists.

Controls:

```text
[ ] public manifests contain only approved data
[ ] raw artifacts remain outside ETS unless approved
[ ] claim-boundary text appears on every public certificate
[ ] public verifier rejects tampered proof bundles
[ ] public verifier can run offline against downloaded proof bundles
```

## 5. Repository hardening checklist

Before the repo is made public, verify:

```text
[ ] secret scanning enabled
[ ] push protection enabled
[ ] Dependabot alerts enabled
[ ] Dependabot security updates enabled
[ ] dependency graph enabled
[ ] CodeQL or code scanning enabled
[ ] branch protection or ruleset on main
[ ] required pull requests before merge
[ ] required checks before merge
[ ] force pushes blocked
[ ] branch deletion blocked
[ ] SECURITY.md present
[ ] PR template includes secret/PII/IP boundary checks
```

GitHub push protection should be treated as a guardrail, not a replacement for careful review. Contributors should still scan local changes and avoid creating sensitive test fixtures.

## 6. Local secret scanning pattern

Add a local pre-push routine outside the public repo or in a developer script. Example using common shell tools:

```powershell
git diff --cached --name-only | ForEach-Object {
  Select-String -Path $_ -Pattern "AKIA|BEGIN PRIVATE KEY|ghp_|xoxb-|api[_-]?key|secret|password|token" -SimpleMatch:$false
}
```

This is not sufficient by itself. Use dedicated scanners when available, and rely on GitHub secret scanning/push protection at the repository boundary.

## 7. API hardening baseline

### 7.1 Run with explicit environment variables

Do not rely on mystery defaults in shared environments.

```powershell
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets-validation.db"
$env:ETS_REDACTION_PROFILE = "basic_pii"
$env:ETS_AUTH_MODE = "production_jwks"
$env:ETS_AUTH_JWKS_URL = "https://issuer.example/.well-known/jwks.json"
$env:ETS_AUTH_ISSUER = "https://issuer.example/"
$env:ETS_AUTH_AUDIENCE = "ets-api"
$env:ETS_SIGNING_MODE = "ed25519"
$env:ETS_SIGNING_PUBLIC_KEY_ID = "ets-validation-key-2026-01"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --host 127.0.0.1 --port 8000
```

Bind to `127.0.0.1` unless a reverse proxy or controlled network boundary is ready.

### 7.2 Require tenant/workspace scope

Callers should not be allowed to write unscoped records in shared environments.

Example policy wrapper:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthContext:
    subject: str
    roles: set[str]
    tenant_id: str | None
    workspace_id: str | None


def require_scope(context: AuthContext) -> None:
    if not context.tenant_id or not context.workspace_id:
        raise PermissionError("tenant_id and workspace_id are required")


def require_role(context: AuthContext, role: str) -> None:
    if role not in context.roles:
        raise PermissionError(f"missing required role: {role}")
```

### 7.3 Reject cross-tenant reads

A lookup mismatch should return not found, not a detailed cross-tenant error.

```python
def authorize_event_read(*, event_tenant: str, event_workspace: str, context: AuthContext) -> None:
    require_scope(context)
    if event_tenant != context.tenant_id or event_workspace != context.workspace_id:
        raise LookupError("event not found")
```

## 8. Evidence intake controls

Validate every event before append.

```python
from __future__ import annotations

from ets.core import EvidenceEvent


ALLOWED_EVENT_TYPES = {
    "workflow.evidence",
    "ai.output.generated",
    "ci.build.completed",
    "election.logic_accuracy_test.completed",
    "incident.timeline.hashed",
}


def validate_event_for_intake(event: EvidenceEvent) -> None:
    if event.event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event.event_type}")
    if event.content_hash_alg != "sha256":
        raise ValueError("only sha256 is allowed in this profile")
    if len(event.content_hash) != 64:
        raise ValueError("content_hash must be a sha256 hex digest")
    if event.metadata.get("fictional") is not True and event.redaction_profile == "none":
        raise ValueError("non-fictional events require a redaction profile")
```

## 9. Redaction profile baseline

Use metadata profiles intentionally.

| Profile | Use | Public release allowed? |
|---|---|---|
| `none` | Synthetic local demos only. | Yes, if fictional. |
| `basic_pii` | Internal tests where obvious PII patterns are removed before ETS. | Usually no without review. |
| `strict` | Regulated, civic-sensitive, legal, healthcare, incident, or customer evidence. | No without explicit public-release approval. |

Example metadata minimizer:

```python
from __future__ import annotations

SENSITIVE_KEYS = {"name", "email", "phone", "address", "ssn", "dob", "license", "token", "password"}


def minimize_metadata(metadata: dict[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_KEYS:
            safe[f"{key}_redacted"] = True
        else:
            safe[key] = value
    return safe
```

## 10. Certificate hardening

A certificate must be claim-safe by construction.

Required certificate sections:

```text
what was submitted
hash algorithm and event hash
proof type and tree head
verification result
verifier version
policy route
claim boundary
non-claims
```

Required non-claim language:

```text
This certificate verifies submitted-event metadata, content hashes, inclusion proofs, tree-head material, verifier output, and policy-routing records. It does not prove real-world truth, legal sufficiency, official chain of custody, election correctness, raw evidence authenticity, or completeness without an external expected-event policy and observation process.
```

Test it:

```python
def assert_certificate_boundary(text: str) -> None:
    required = [
        "does not prove real-world truth",
        "legal sufficiency",
        "official chain of custody",
        "completeness without an external expected-event policy",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    if missing:
        raise AssertionError(f"certificate missing boundary language: {missing}")
```

## 11. Audit logging controls

Audit logs should record security-relevant actions without leaking secret values.

Record:

```text
request id
actor subject
tenant/workspace
event id
operation
result
error class
policy decision
verification status
timestamp
```

Do not record:

```text
bearer tokens
API keys
raw private evidence
raw PHI/PII
private keys
passwords
```

Example event-safe audit record:

```python
from datetime import UTC, datetime


def audit_record(*, actor: str, operation: str, event_id: str, result: str) -> dict[str, str]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "actor": actor,
        "operation": operation,
        "event_id": event_id,
        "result": result,
    }
```

## 12. Backup and restore controls

For SQLite validation:

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
Copy-Item .\.data\ets-validation.db .\backups\ets-validation-$(Get-Date -Format yyyyMMdd-HHmmss).db
```

Restore test:

```powershell
Copy-Item .\backups\ets-validation-demo.db .\.data\ets-validation-restored.db
$env:ETS_SQLITE_PATH = ".data\ets-validation-restored.db"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
Invoke-RestMethod http://localhost:8000/ready
```

Done criteria:

```text
[ ] restored database starts
[ ] log head is readable
[ ] prior proof bundle can be retrieved
[ ] certificate can be regenerated
[ ] tamper test still fails correctly
```

## 13. Deployment kill switches

Add operational switches before public pilots:

```text
ETS_PUBLIC_MANIFEST_ENABLED=false
ETS_EXTERNAL_ANCHOR_EXPORT_ENABLED=false
ETS_AUTOMATION_APPROVAL_ENABLED=false
ETS_REQUIRE_HUMAN_REVIEW_FOR_CIVIC=true
ETS_REQUIRE_HUMAN_REVIEW_FOR_REGULATED=true
```

Policy should fail closed:

```python
def require_feature_enabled(flag_value: str | None, feature_name: str) -> None:
    if flag_value != "true":
        raise PermissionError(f"feature disabled: {feature_name}")
```

## 14. Release gate checklist

Before any public deployment or public demo release:

```text
[ ] all examples synthetic or explicitly public
[ ] no secrets in repository or artifacts
[ ] auth enabled for write APIs
[ ] tenant/workspace scoping tested
[ ] proof tamper tests pass
[ ] consistency proof tests pass
[ ] certificate boundary tests pass
[ ] public manifest reviewed
[ ] backup/restore tested
[ ] key rotation plan documented
[ ] incident response playbook drafted
[ ] production non-claims visible
[ ] legal/civic/election non-claims visible where applicable
```

## 15. Operator incident playbook

When something goes wrong:

1. Freeze public manifest publication.
2. Disable automation approval routes.
3. Preserve logs, tree heads, proof bundles, and environment configuration.
4. Rotate exposed secrets or keys.
5. Mark affected tree heads or certificates as under review.
6. Publish a bounded correction if public artifacts were released.
7. Re-run verification and replay reports after remediation.

Use this language:

```text
The affected ETS evidence record is under review. ETS verification confirms only the submitted proof material. The review does not alter any official record, legal conclusion, election result, or external source-of-truth process.
```

## 16. References for implementers

- NIST SP 800-218 SSDF: secure software development practices.
- NIST Cybersecurity Framework: governance, identification, protection, detection, response, and recovery framing.
- OWASP ASVS: application security verification controls.
- GitHub secret scanning and push protection: repository boundary controls.
- CISA Zero Trust Maturity Model: identity, device, network, application/workload, data, visibility, automation, and governance framing.

## 17. Minimum hardening definition

A minimally hardened ETS validation environment has:

```text
[ ] authenticated write APIs
[ ] tenant/workspace scoping
[ ] synthetic or approved evidence only
[ ] metadata minimization
[ ] secret scanning and push protection
[ ] durable store backup/restore
[ ] verifier tamper tests
[ ] certificate boundary tests
[ ] no public automation approval for sensitive evidence
[ ] visible non-claim language
```
