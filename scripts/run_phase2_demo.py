"""Phase 2 enterprise explorer/API demo payload.

The demo is deterministic and CLI-friendly so `npm run demo:phase2` can be used
in local validation, CI, and screenshots without starting a hosted service.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ets.core.log import InMemoryAppendOnlyLog  # noqa: E402
from ets.core.models import EvidenceEvent  # noqa: E402
from ets.core.proofs import generate_inclusion_proof, verify_inclusion_proof  # noqa: E402


def run_demo() -> dict[str, Any]:
    artifact = b"phase-2 enterprise explorer artifact"
    tampered_artifact = artifact + b"!"
    content_hash = hashlib.sha256(artifact).hexdigest()
    tampered_hash = hashlib.sha256(tampered_artifact).hexdigest()
    created_at = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)

    log = InMemoryAppendOnlyLog()
    entry = log.append(
        EvidenceEvent(
            event_id="phase2-artifact-001",
            tenant_id="tenant-demo",
            workspace_id="enterprise-demo",
            evidence_id="artifact-001",
            event_type="artifact.registered",
            subject_ref="demo://phase2/artifact-001",
            content_hash=content_hash,
            content_hash_alg="sha256",
            metadata={"explorerTimeline": "upload -> proof -> verify -> tamper"},
            created_at_utc=created_at,
            source_system="phase2-demo",
            actor_id="demo-user",
            correlation_id="phase2-demo",
        )
    )
    proof = generate_inclusion_proof(log.list_entries(), entry.log_index, created_at)
    verification = verify_inclusion_proof(proof)
    tampered_verification = content_hash == tampered_hash and verification.valid

    return {
        "demo": "phase2-enterprise-explorer",
        "steps": [
            "upload artifact",
            "generate proof",
            "view explorer timeline",
            "verify artifact",
            "simulate tampering",
            "display failed verification",
        ],
        "apiSurface": [
            "evidence registration",
            "proof retrieval",
            "chain verification",
            "Merkle proof verification",
            "signed tree head retrieval",
        ],
        "azurePath": [
            "Azure App Service or Container Apps for ETS API",
            "Azure Static Web Apps for Explorer UI",
            "Azure Storage immutable blob policies for evidence/proof exports",
            "Azure Monitor structured logs and replay jobs",
        ],
        "artifact": {
            "eventId": entry.event.event_id,
            "contentHash": content_hash,
            "proofRoot": proof.root_hash,
        },
        "verification": verification.model_dump(mode="json"),
        "tamperSimulation": {
            "tamperedContentHash": tampered_hash,
            "valid": tampered_verification,
            "reason": "content hash mismatch",
        },
    }


def main() -> None:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
