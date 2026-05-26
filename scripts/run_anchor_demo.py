from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ets.api.app import create_app  # noqa: E402
from ets.core.models import EvidenceEvent  # noqa: E402


def make_demo_event(index: int) -> dict[str, object]:
    event = EvidenceEvent(
        event_id=f"evt_anchor_{index:03d}",
        tenant_id="tenant_demo",
        workspace_id="workspace_demo",
        evidence_id=f"evidence_anchor_{index:03d}",
        event_type="evidence.registered",
        subject_ref=None,
        content_hash=f"{index + 17:064x}"[-64:],
        content_hash_alg="sha256",
        metadata={"demo": "external-anchor", "contains_real_pii": False},
        created_at_utc=datetime(2026, 5, 26, 15, index, tzinfo=UTC),
    )
    return event.model_dump(mode="json")


def run_demo() -> dict[str, object]:
    client = TestClient(create_app())
    for index in range(3):
        response = client.post("/api/v1/events", json=make_demo_event(index))
        response.raise_for_status()

    export_response = client.get("/anchors/latest?target=github_release")
    export_response.raise_for_status()
    anchor = export_response.json()

    verify_response = client.post("/verify/anchor", json=anchor)
    verify_response.raise_for_status()

    tampered_anchor = dict(anchor)
    tampered_anchor["merkle_root"] = "0" * 64
    tampered_response = client.post("/verify/anchor", json=tampered_anchor)
    tampered_response.raise_for_status()

    history_response = client.get("/anchors/history")
    history_response.raise_for_status()

    return {
        "demo": "external-anchor",
        "exported_anchor_id": anchor["anchor_id"],
        "target": anchor["target"],
        "tree_size": anchor["tree_size"],
        "latest_block_hash": anchor["latest_block_hash"],
        "merkle_root": anchor["merkle_root"],
        "verified_anchor": verify_response.json(),
        "tampered_anchor": tampered_response.json(),
        "history_count": len(history_response.json()),
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
