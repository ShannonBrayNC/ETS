"""Deterministic local upstream sink for ETS Edge synchronization demos."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status

DEFAULT_UPSTREAM_DB = "/var/lib/ets-upstream/upstream.db"
MAX_SYNC_BODY_BYTES = 256 * 1024

app = FastAPI(
    title="ETS Edge Demo Upstream",
    version="0.1.0",
    description="Idempotent development/evaluation sink for ETS Edge synchronization",
)


@app.get("/health")
def health() -> dict[str, str]:
    _initialize()
    return {"status": "ok", "component": "edge-demo-upstream"}


@app.get("/edge/v1/upstream/status")
def upstream_status() -> dict[str, int | str]:
    with _connect() as connection:
        _initialize_connection(connection)
        row = connection.execute("SELECT COUNT(*) FROM upstream_records").fetchone()
        count = 0 if row is None else int(row[0])
    return {"status": "online", "accepted_records": count}


@app.post("/edge/v1/upstream/records", status_code=status.HTTP_200_OK)
async def ingest_record(request: Request) -> dict[str, object]:
    body = await request.body()
    if len(body) > MAX_SYNC_BODY_BYTES:
        raise HTTPException(status_code=413, detail="sync envelope exceeds 256 KiB limit")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="sync envelope must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="sync envelope must be a JSON object")

    required = _validate_payload(payload)
    payload_json = _canonical_json(payload)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    checkpoint_root, checkpoint_size = _checkpoint(payload)

    with _connect() as connection:
        _initialize_connection(connection)
        row = connection.execute(
            "SELECT * FROM upstream_records WHERE idempotency_key = ?",
            (required["idempotency_key"],),
        ).fetchone()
        if row is not None:
            if row["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency key conflicts with previously accepted immutable content",
                )
            return _ack_from_row(row)

        cursor = connection.execute(
            """
            INSERT INTO upstream_records (
                idempotency_key, event_id, event_hash, tenant_id, workspace_id,
                payload_hash, checkpoint_root, checkpoint_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                required["idempotency_key"],
                required["event_id"],
                required["event_hash"],
                required["tenant_id"],
                required["workspace_id"],
                payload_hash,
                checkpoint_root,
                checkpoint_size,
            ),
        )
        row = connection.execute(
            "SELECT * FROM upstream_records WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    if row is None:
        raise RuntimeError("failed to load accepted upstream record")
    return _ack_from_row(row)


def _validate_payload(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("sync_schema") != "ets.edge.sync.v1":
        raise HTTPException(status_code=422, detail="unsupported sync schema")
    if payload.get("raw_payload_included") is not False:
        raise HTTPException(
            status_code=422,
            detail="raw evidence replication is disabled in demo profile",
        )
    fields: dict[str, str] = {}
    for name in ("idempotency_key", "event_id", "event_hash", "tenant_id", "workspace_id"):
        value = payload.get(name)
        if not isinstance(value, str) or not value:
            raise HTTPException(status_code=422, detail=f"missing sync field: {name}")
        fields[name] = value
    return fields


def _checkpoint(payload: dict[str, Any]) -> tuple[str, int]:
    tree_head = payload.get("tree_head")
    if not isinstance(tree_head, dict):
        raise HTTPException(status_code=422, detail="signed tree_head is required")
    root_hash = tree_head.get("root_hash")
    tree_size = tree_head.get("tree_size")
    signature = tree_head.get("signature")
    if not isinstance(root_hash, str) or not root_hash:
        raise HTTPException(status_code=422, detail="tree_head root_hash is required")
    if not isinstance(tree_size, int) or tree_size < 0:
        raise HTTPException(status_code=422, detail="tree_head tree_size is invalid")
    if not isinstance(signature, str) or not signature:
        raise HTTPException(status_code=422, detail="signed tree_head signature is required")
    return root_hash, tree_size


def _ack_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "status": "accepted",
        "logical_sequence": int(row["id"]),
        "idempotency_key": str(row["idempotency_key"]),
        "event_id": str(row["event_id"]),
        "event_hash": str(row["event_hash"]),
        "accepted_checkpoint_root": str(row["checkpoint_root"]),
        "accepted_checkpoint_size": int(row["checkpoint_size"]),
    }


def _initialize() -> None:
    with _connect() as connection:
        _initialize_connection(connection)


def _initialize_connection(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS upstream_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT NOT NULL UNIQUE,
            event_id TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            checkpoint_root TEXT NOT NULL,
            checkpoint_size INTEGER NOT NULL
        )
        """
    )


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("ETS_EDGE_UPSTREAM_DB", DEFAULT_UPSTREAM_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
