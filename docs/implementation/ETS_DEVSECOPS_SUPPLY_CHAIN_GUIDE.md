# ETS DevSecOps and Software Supply Chain Guide

Version: v0.1.0-alpha guide  
Status: public-safe implementation guide  
Audience: DevSecOps engineers, platform teams, release managers, security reviewers, and CI/CD maintainers

## 1. Purpose

Software delivery pipelines already produce useful artifacts: commits, pull requests, workflow runs, test reports, SBOMs, container digests, vulnerability scans, approvals, releases, deployments, and rollbacks. ETS can preserve hashes and metadata for those artifacts as proof-bearing evidence events.

This guide explains how to integrate ETS into DevSecOps and software supply chain workflows without claiming ETS replaces secure software development, artifact signing, SBOM standards, transparency services, or release governance.

## 2. Standards context

NIST SSDF provides high-level secure software development practices for reducing software vulnerability risk. SCITT defines an architecture for transparency services and receipts for signed supply-chain statements. Sigstore/Rekor and related systems provide software artifact transparency and signing workflows. ETS should interoperate beside those systems, not pretend to replace them.

ETS contributes a cross-workflow evidence layer: it can record that pipeline artifacts and approvals were submitted, hashed, included, verified, certified, and routed.

## 3. DevSecOps event taxonomy

| Phase | Event type | Evidence artifact |
|---|---|---|
| Source | `git.commit.hashed` | Commit metadata, tree hash, author id, timestamp. |
| Review | `git.pr.opened` | PR metadata hash. |
| Review | `git.pr.reviewed` | Review decision hash and reviewer role. |
| Build | `ci.workflow.completed` | Workflow run summary. |
| Build | `ci.test_report.hashed` | Test report artifact. |
| Build | `ci.coverage_report.hashed` | Coverage report. |
| Supply chain | `supply.sbom.hashed` | SBOM file hash. |
| Supply chain | `supply.artifact_digest.recorded` | Container/image/package digest. |
| Security | `security.scan.completed` | Vulnerability or static-analysis report hash. |
| Release | `release.approval.recorded` | Approval packet. |
| Release | `release.manifest.published` | Release manifest hash. |
| Deploy | `deploy.completed` | Deployment record hash. |
| Recovery | `deploy.rollback.completed` | Rollback decision and result hash. |

## 4. Minimum metadata

```json
{
  "repository": "ShannonBrayNC/ETS",
  "commit_sha": "hex or fictional sha",
  "branch": "main",
  "workflow_name": "CI",
  "workflow_run_id": "fictional-run-001",
  "artifact_type": "test_report",
  "artifact_hash": "sha256 hex string",
  "artifact_uri": "fictional://ci/artifacts/test-report.json",
  "policy_version": "devsecops-policy-v1",
  "requested_action": "approve_release",
  "sensitivity": "internal",
  "claim_boundary": "ETS verifies submitted pipeline artifact hash and metadata only."
}
```

## 5. Hash a CI artifact

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

## 6. Build a workflow EvidenceEvent

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.core import EvidenceEvent


def build_workflow_event(
    *,
    repository: str,
    commit_sha: str,
    branch: str,
    workflow_name: str,
    workflow_run_id: str,
    artifact_path: str | Path,
    artifact_type: str,
    tenant_id: str = "devsecops-demo",
    workspace_id: str = "software-supply-chain",
) -> EvidenceEvent:
    artifact_hash = sha256_file(artifact_path)
    event_id = f"evt-ci-{workflow_run_id}-{artifact_type}"
    return EvidenceEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        evidence_id=f"ci-artifact-{workflow_run_id}-{artifact_type}",
        event_type="ci.workflow_artifact.hashed",
        subject_ref=f"fictional://ci/{repository}/{workflow_run_id}/{artifact_type}",
        content_hash=artifact_hash,
        content_hash_alg="sha256",
        metadata={
            "repository": repository,
            "commit_sha": commit_sha,
            "branch": branch,
            "workflow_name": workflow_name,
            "workflow_run_id": workflow_run_id,
            "artifact_type": artifact_type,
            "artifact_hash": artifact_hash,
            "policy_version": "devsecops-policy-v1",
            "requested_action": "approve_release",
            "sensitivity": "internal",
            "claim_boundary": "ETS verifies submitted CI artifact hash and metadata only.",
        },
        created_at_utc=datetime.now(UTC),
        source_system="github-actions-demo",
        actor_id="ci:github-actions",
        correlation_id=f"ci-{workflow_run_id}",
        external_refs={"repository": repository, "commit_sha": commit_sha, "workflow_run_id": workflow_run_id},
        redaction_profile="none",
    )
```

## 7. Record SBOM evidence

```python
def build_sbom_event(
    *,
    repository: str,
    commit_sha: str,
    sbom_path: str | Path,
    sbom_format: str,
    workflow_run_id: str,
) -> EvidenceEvent:
    sbom_hash = sha256_file(sbom_path)
    return EvidenceEvent(
        event_id=f"evt-sbom-{workflow_run_id}",
        tenant_id="devsecops-demo",
        workspace_id="software-supply-chain",
        evidence_id=f"sbom-{workflow_run_id}",
        event_type="supply.sbom.hashed",
        subject_ref=f"fictional://sbom/{repository}/{commit_sha}",
        content_hash=sbom_hash,
        content_hash_alg="sha256",
        metadata={
            "repository": repository,
            "commit_sha": commit_sha,
            "sbom_format": sbom_format,
            "sbom_hash": sbom_hash,
            "requested_action": "approve_release",
            "sensitivity": "internal",
            "claim_boundary": "ETS verifies submitted SBOM hash and metadata only.",
        },
        created_at_utc=datetime.now(UTC),
        source_system="sbom-generator-demo",
        actor_id="ci:sbom",
        correlation_id=f"sbom-{workflow_run_id}",
        external_refs={"repository": repository, "commit_sha": commit_sha},
        redaction_profile="none",
    )
```

## 8. Record container digest evidence

```python
def build_container_digest_event(
    *,
    image_name: str,
    image_digest: str,
    repository: str,
    commit_sha: str,
    workflow_run_id: str,
) -> EvidenceEvent:
    digest_bytes = image_digest.encode("utf-8")
    return EvidenceEvent(
        event_id=f"evt-image-digest-{workflow_run_id}",
        tenant_id="devsecops-demo",
        workspace_id="software-supply-chain",
        evidence_id=f"image-digest-{workflow_run_id}",
        event_type="supply.artifact_digest.recorded",
        subject_ref=f"fictional://container/{image_name}",
        content_hash=sha256(digest_bytes).hexdigest(),
        content_hash_alg="sha256",
        metadata={
            "image_name": image_name,
            "image_digest": image_digest,
            "repository": repository,
            "commit_sha": commit_sha,
            "workflow_run_id": workflow_run_id,
            "requested_action": "approve_release",
            "sensitivity": "internal",
        },
        created_at_utc=datetime.now(UTC),
        source_system="container-registry-demo",
        actor_id="ci:release",
        correlation_id=f"image-{workflow_run_id}",
        external_refs={"image_name": image_name, "image_digest": image_digest},
        redaction_profile="none",
    )
```

## 9. Release gate integration

A release gate should require evidence for tests, scan, SBOM, artifact digest, approval, and release manifest.

```python
REQUIRED_RELEASE_EVENTS = {
    "ci.test_report.hashed",
    "security.scan.completed",
    "supply.sbom.hashed",
    "supply.artifact_digest.recorded",
    "release.approval.recorded",
    "release.manifest.published",
}


def release_gate_ready(events: list[dict[str, object]]) -> tuple[bool, list[str]]:
    observed = {str(event["event_type"]) for event in events}
    missing = sorted(REQUIRED_RELEASE_EVENTS - observed)
    return not missing, missing
```

Safe language:

```text
The release gate can show whether required ETS evidence events were submitted and verified for this release policy. It does not prove the software is vulnerability-free, legally compliant, safe to deploy, or free from supply-chain compromise.
```

## 10. GitHub Actions pattern

```yaml
name: ETS Evidence Capture

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

permissions:
  contents: read

jobs:
  capture-evidence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Produce fictional evidence packet
        run: |
          mkdir -p artifacts
          printf '{"workflow":"CI","status":"fictional"}' > artifacts/ci-summary.json
      - name: Hash artifact
        run: |
          python - <<'PY'
          from hashlib import sha256
          from pathlib import Path
          p = Path('artifacts/ci-summary.json')
          print(sha256(p.read_bytes()).hexdigest())
          PY
```

For public PRs, do not expose secrets to forked workflows. Keep ETS publication gated by maintainer-controlled release workflows.

## 11. Certificate wording

```text
This certificate verifies the submitted CI/CD artifact hash, event metadata, inclusion proof, tree-head material, verifier version, and policy route. It does not prove the artifact is secure, vulnerability-free, legally compliant, or safe to deploy.
```

## 12. Tests

```python
def test_release_gate_reports_missing_events() -> None:
    events = [{"event_type": "ci.test_report.hashed"}]
    ready, missing = release_gate_ready(events)
    assert ready is False
    assert "supply.sbom.hashed" in missing


def test_container_digest_event_uses_digest_as_metadata() -> None:
    event = build_container_digest_event(
        image_name="example/ets:demo",
        image_digest="sha256:fictional",
        repository="ShannonBrayNC/ETS",
        commit_sha="abc123",
        workflow_run_id="run-1",
    )
    assert event.metadata["image_digest"] == "sha256:fictional"
    assert event.event_type == "supply.artifact_digest.recorded"
```

## 13. Operator checklist

```text
[ ] CI evidence uses synthetic public examples in docs and tests.
[ ] Release gate requires proof bundle verification before publishing release evidence.
[ ] Forked PR workflows do not receive ETS publication secrets.
[ ] SBOM and artifact digest evidence are separate events.
[ ] Certificate avoids vulnerability-free or secure-by-default claims.
[ ] Release approval is recorded as an ETS event.
[ ] Rollback evidence is recorded when release is reversed.
```

## 14. References

- NIST SSDF: `https://csrc.nist.gov/pubs/sp/800/218/final`
- RFC 9943 / SCITT: `https://www.rfc-editor.org/info/rfc9943/`
- ETS Security Hardening Guide: `docs/implementation/ETS_SECURITY_HARDENING_GUIDE.md`
- ETS Certificate and Public Verifier Guide: `docs/implementation/ETS_CERTIFICATE_PUBLIC_VERIFIER_GUIDE.md`
