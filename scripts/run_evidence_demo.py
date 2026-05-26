from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ets.api.app import create_app  # noqa: E402


def encode_artifact(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")


def run_demo() -> dict[str, object]:
    client = TestClient(create_app())
    original = b'{"demo":"evidence","value":1}'
    tampered = b'{"demo":"evidence","value":2}'
    registration = {
        "artifact_id": "artifact_demo_001",
        "artifact_base64": encode_artifact(original),
        "tenant_id": "tenant_demo",
        "workspace_id": "workspace_demo",
        "content_type": "application/json",
        "metadata": {"demo": "evidence", "contains_real_pii": False},
        "source_system": "local-demo",
    }

    receipt = client.post("/evidence/register", json=registration).json()
    valid = client.post(
        "/evidence/verify",
        json={
            "artifact_id": "artifact_demo_001",
            "artifact_base64": encode_artifact(original),
        },
    ).json()
    invalid = client.post(
        "/evidence/verify",
        json={
            "artifact_id": "artifact_demo_001",
            "artifact_base64": encode_artifact(tampered),
        },
    ).json()
    proof = client.get("/evidence/artifact_demo_001/proof").json()

    return {
        "demo": "evidence-registration",
        "receipt": receipt,
        "valid_artifact": valid,
        "tampered_artifact": invalid,
        "proof_event_id": proof["event"]["event_id"],
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
