from __future__ import annotations

import base64
import sqlite3

from fastapi.testclient import TestClient

from ets.api.app import create_app
from ets.core import SQLiteEventStore


def artifact_payload(artifact_id: str = "artifact-001") -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "artifact_base64": base64.b64encode(b"durable artifact body").decode("ascii"),
        "tenant_id": "tenant-a",
        "workspace_id": "workspace-a",
        "content_type": "text/plain",
        "metadata": {"case": "alpha"},
        "reference_uri": f"ets://artifact/{artifact_id}",
    }


def test_artifact_routes_survive_sqlite_restart(tmp_path) -> None:
    path = tmp_path / "ets.db"
    first_client = TestClient(create_app(log=SQLiteEventStore(path)))

    registration = first_client.post("/evidence/register", json=artifact_payload())

    assert registration.status_code == 201
    assert registration.json()["artifact_id"] == "artifact-001"

    second_client = TestClient(create_app(log=SQLiteEventStore(path)))

    read_response = second_client.get("/evidence/artifact-001")
    proof_response = second_client.get("/evidence/artifact-001/proof")
    verify_response = second_client.post(
        "/evidence/verify",
        json={
            "artifact_id": "artifact-001",
            "artifact_base64": artifact_payload()["artifact_base64"],
        },
    )
    duplicate_response = second_client.post("/evidence/register", json=artifact_payload())

    assert read_response.status_code == 200
    assert read_response.json()["artifact_id"] == "artifact-001"
    assert read_response.json()["metadata"] == {"case": "alpha"}
    assert proof_response.status_code == 200
    assert proof_response.json()["event"]["event_id"] == "artifact_registered:artifact-001"
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert duplicate_response.status_code == 409


def test_artifact_registration_persists_metadata_without_raw_payload(tmp_path) -> None:
    path = tmp_path / "ets.db"
    client = TestClient(create_app(log=SQLiteEventStore(path)))

    registration = client.post("/evidence/register", json=artifact_payload())

    assert registration.status_code == 201
    with sqlite3.connect(path) as connection:
        artifact_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(artifact_records)").fetchall()
        }
        stored_metadata = connection.execute(
            "SELECT metadata_json FROM artifact_records WHERE artifact_id = ?",
            ("artifact-001",),
        ).fetchone()[0]

    assert "artifact_base64" not in artifact_columns
    assert "raw" not in artifact_columns
    assert "durable artifact body" not in stored_metadata
    assert "artifact_base64" not in stored_metadata
