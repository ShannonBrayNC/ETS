param(
    [string]$RepoPath = "C:\GitHub\ETS"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Validating repo path"

if (-not (Test-Path $RepoPath)) {
    throw "Repo path not found: $RepoPath"
}

Set-Location $RepoPath

if (-not (Test-Path ".git")) {
    throw "Not a git repository: $RepoPath"
}

$coreRoot = Join-Path $RepoPath "ets\core"
$pkgRoot  = Join-Path $coreRoot "ets_core"
$testsRoot = Join-Path $RepoPath "tests"

Write-Step "Creating directories"

$dirs = @(
    $coreRoot,
    $pkgRoot,
    $testsRoot
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Step "Writing Python package files"

@"
__all__ = [
    "canonical",
    "hashing",
    "merkle",
    "storage",
    "service"
]
"@ | Set-Content -Path (Join-Path $pkgRoot "__init__.py") -Encoding utf8

@"
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """
    Produce canonical JSON bytes:
    - UTF-8 encoded
    - sorted keys
    - no extra whitespace
    - preserve Unicode characters
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")
"@ | Set-Content -Path (Join-Path $pkgRoot "canonical.py") -Encoding utf8

@"
import hashlib
from typing import Any
from .canonical import canonical_json_bytes


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def hash_leaf(event_id: str, timestamp_utc: str, payload_hash: str, event_type: str, metadata: dict | None = None) -> str:
    envelope = {
        "event_id": event_id,
        "timestamp_utc": timestamp_utc,
        "type": event_type,
        "payload_hash": payload_hash,
        "metadata": metadata or {}
    }
    return sha256_hex(canonical_json_bytes(envelope))
"@ | Set-Content -Path (Join-Path $pkgRoot "hashing.py") -Encoding utf8

@"
import hashlib
from typing import List


def _hash_pair(left_hex: str, right_hex: str) -> str:
    data = bytes.fromhex(left_hex) + bytes.fromhex(right_hex)
    return hashlib.sha256(data).hexdigest()


def merkle_root(leaves: List[str]) -> str:
    if not leaves:
        return hashlib.sha256(b"").hexdigest()

    level = leaves[:]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(_hash_pair(left, right))
        level = next_level
    return level[0]


def inclusion_proof(leaves: List[str], index: int) -> List[dict]:
    if index < 0 or index >= len(leaves):
        raise IndexError("Leaf index out of range")

    proof = []
    level = leaves[:]
    idx = index

    while len(level) > 1:
        next_level = []

        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left

            if i == idx or i + 1 == idx:
                if idx == i:
                    sibling = right
                    position = "right"
                else:
                    sibling = left
                    position = "left"
                proof.append({
                    "position": position,
                    "hash": sibling
                })

            next_level.append(_hash_pair(left, right))

        idx = idx // 2
        level = next_level

    return proof


def verify_inclusion(leaf_hash: str, proof: List[dict], expected_root: str) -> bool:
    current = leaf_hash
    for step in proof:
        sibling = step["hash"]
        position = step["position"]

        if position == "left":
            current = _hash_pair(sibling, current)
        elif position == "right":
            current = _hash_pair(current, sibling)
        else:
            raise ValueError(f"Invalid proof position: {position}")

    return current == expected_root
"@ | Set-Content -Path (Join-Path $pkgRoot "merkle.py") -Encoding utf8

@"
import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    timestamp_utc TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    leaf_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
'''


class EventStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)
            conn.commit()

    def insert_event(
        self,
        event_id: str,
        timestamp_utc: str,
        event_type: str,
        payload_json: str,
        payload_hash: str,
        leaf_hash: str,
        metadata_json: str
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                '''
                INSERT INTO events (event_id, timestamp_utc, type, payload_json, payload_hash, leaf_hash, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (event_id, timestamp_utc, event_type, payload_json, payload_hash, leaf_hash, metadata_json)
            )
            conn.commit()
            return cur.lastrowid

    def get_event_by_event_id(self, event_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM events WHERE event_id = ?",
                (event_id,)
            )
            return cur.fetchone()

    def list_events(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM events ORDER BY id ASC"
            )
            return cur.fetchall()
"@ | Set-Content -Path (Join-Path $pkgRoot "storage.py") -Encoding utf8

@"
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .canonical import canonical_json_bytes
from .hashing import hash_payload, hash_leaf
from .merkle import merkle_root, inclusion_proof, verify_inclusion
from .storage import EventStore


class TransparencyLogService:
    def __init__(self, db_path: str):
        self.store = EventStore(db_path)

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def append_event(self, payload: Any, event_type: str, metadata: dict | None = None, event_id: str | None = None) -> dict:
        event_id = event_id or str(uuid.uuid4())
        timestamp_utc = self.utc_now_iso()
        payload_hash = hash_payload(payload)
        leaf_hash = hash_leaf(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            payload_hash=payload_hash,
            event_type=event_type,
            metadata=metadata or {}
        )

        self.store.insert_event(
            event_id=event_id,
            timestamp_utc=timestamp_utc,
            event_type=event_type,
            payload_json=canonical_json_bytes(payload).decode("utf-8"),
            payload_hash=payload_hash,
            leaf_hash=leaf_hash,
            metadata_json=canonical_json_bytes(metadata or {}).decode("utf-8")
        )

        return {
            "event_id": event_id,
            "timestamp_utc": timestamp_utc,
            "type": event_type,
            "payload_hash": payload_hash,
            "leaf_hash": leaf_hash
        }

    def get_event(self, event_id: str) -> dict | None:
        row = self.store.get_event_by_event_id(event_id)
        if row is None:
            return None

        return {
            "id": row["id"],
            "event_id": row["event_id"],
            "timestamp_utc": row["timestamp_utc"],
            "type": row["type"],
            "payload_json": json.loads(row["payload_json"]),
            "payload_hash": row["payload_hash"],
            "leaf_hash": row["leaf_hash"],
            "metadata_json": json.loads(row["metadata_json"])
        }

    def tree_head(self) -> dict:
        rows = self.store.list_events()
        leaves = [row["leaf_hash"] for row in rows]
        root = merkle_root(leaves)
        return {
            "tree_size": len(leaves),
            "root_hash": root
        }

    def proof_for_event(self, event_id: str) -> dict | None:
        rows = self.store.list_events()
        leaves = [row["leaf_hash"] for row in rows]

        target_index = None
        target_row = None

        for idx, row in enumerate(rows):
            if row["event_id"] == event_id:
                target_index = idx
                target_row = row
                break

        if target_index is None or target_row is None:
            return None

        root = merkle_root(leaves)
        proof = inclusion_proof(leaves, target_index)

        return {
            "event_id": event_id,
            "leaf_hash": target_row["leaf_hash"],
            "tree_size": len(leaves),
            "root_hash": root,
            "proof": proof
        }

    def verify_payload_against_event(self, event_id: str, payload: Any) -> dict | None:
        event = self.get_event(event_id)
        if event is None:
            return None

        candidate_hash = hash_payload(payload)
        matches = candidate_hash == event["payload_hash"]

        proof_bundle = self.proof_for_event(event_id)
        included = False
        if proof_bundle:
            included = verify_inclusion(
                leaf_hash=proof_bundle["leaf_hash"],
                proof=proof_bundle["proof"],
                expected_root=proof_bundle["root_hash"]
            )

        return {
            "event_id": event_id,
            "payload_hash_matches": matches,
            "included_in_tree": included,
            "expected_payload_hash": event["payload_hash"],
            "candidate_payload_hash": candidate_hash
        }
"@ | Set-Content -Path (Join-Path $pkgRoot "service.py") -Encoding utf8

Write-Step "Writing core README"

@"
# ETS Core Prototype

This directory contains the first ETS transparency log prototype.

## Features

- canonical JSON hashing
- append-only SQLite event store
- Merkle root generation
- inclusion proof generation
- payload verification against stored records

## Python package

- `ets_core/canonical.py`
- `ets_core/hashing.py`
- `ets_core/merkle.py`
- `ets_core/storage.py`
- `ets_core/service.py`

## Notes

This is the trust engine only. API exposure comes next under `ets/api`.
"@ | Set-Content -Path (Join-Path $coreRoot "README.md") -Encoding utf8

Write-Step "Writing requirements"

@"
pytest==8.3.5
"@ | Set-Content -Path (Join-Path $coreRoot "requirements.txt") -Encoding utf8

Write-Step "Writing starter tests"

@"
from ets.core.ets_core.hashing import hash_payload
from ets.core.ets_core.merkle import merkle_root, inclusion_proof, verify_inclusion
from ets.core.ets_core.service import TransparencyLogService


def test_hash_payload_is_stable():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert hash_payload(a) == hash_payload(b)


def test_merkle_proof_round_trip():
    leaves = [
        "00" * 32,
        "11" * 32,
        "22" * 32,
        "33" * 32
    ]
    root = merkle_root(leaves)
    proof = inclusion_proof(leaves, 2)
    assert verify_inclusion(leaves[2], proof, root) is True


def test_append_and_verify(tmp_path):
    db_path = tmp_path / "ets.db"
    svc = TransparencyLogService(str(db_path))

    payload = {"doc": "hello", "version": 1}
    result = svc.append_event(payload=payload, event_type="document")

    verify = svc.verify_payload_against_event(result["event_id"], payload)
    assert verify is not None
    assert verify["payload_hash_matches"] is True
    assert verify["included_in_tree"] is True
"@ | Set-Content -Path (Join-Path $testsRoot "test_ets_core.py") -Encoding utf8

Write-Step "Writing pyproject for import friendliness"

@"
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ets-core"
version = "0.1.0"
description = "ETS transparency log core prototype"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
"@ | Set-Content -Path (Join-Path $RepoPath "pyproject.toml") -Encoding utf8

Write-Step "Reviewing changes"
git status

Write-Step "Committing prototype"
git add .
git commit -m "Add ETS transparency log core prototype"

Write-Step "Pushing to GitHub"
git push origin main

Write-Step "Done"
Write-Host "ETS transparency log prototype installed successfully." -ForegroundColor Green