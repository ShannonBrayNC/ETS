"""Safety tests for the resumable Azure migration prefix preflight."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_prefix_preflight import (
    _validated_state,
    capture_source_manifest,
    verify_destination_prefix,
)


def _entities(count: int, *, changed_hash_at: int | None = None) -> list[dict[str, object]]:
    partition = "log-test"
    rows: list[dict[str, object]] = [
        {
            "PartitionKey": partition,
            "RowKey": "meta",
            "kind": "metadata",
            "next_index": count,
            "schema_version": 1,
            "log_id": "ets-live-primary",
        }
    ]
    for index in range(count):
        event_id = f"event-{index}"
        event_hash = f"hash-{index}"
        if changed_hash_at == index:
            event_hash = f"changed-{index}"
        rows.extend(
            [
                {
                    "PartitionKey": partition,
                    "RowKey": f"entry-{index:020d}",
                    "kind": "entry",
                    "log_index": index,
                    "event_json": json.dumps({"event_id": event_id}),
                    "event_hash": event_hash,
                    "leaf_hash": f"leaf-{index}",
                },
                {
                    "PartitionKey": partition,
                    "RowKey": "event-" + hashlib.sha256(event_id.encode()).hexdigest(),
                    "kind": "event_index",
                    "event_id": event_id,
                    "log_index": index,
                },
            ]
        )
    return rows


class PrefixPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_env = {
            "MIGRATION_RESOURCE_GROUP": "rg-source",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "ets-gateway-state-q1-v2",
        }
        self.destination_env = {
            "MIGRATION_RESOURCE_GROUP": "rg-destination",
            "MIGRATION_EVIDENCE_TABLE": "ETSEvents",
            "MIGRATION_GATEWAY_SHARE": "ets-gateway-state-q1-v2",
        }

    def test_validated_state_matches_two_rows_per_event(self) -> None:
        state = _validated_state(_entities(3))
        self.assertEqual(state["next_index"], 3)
        self.assertEqual(state["entity_count"], 7)
        self.assertEqual(len(state["pair_digests"]), 3)

    def test_capture_and_verify_accept_exact_destination_prefix(self) -> None:
        calls: list[list[str]] = []
        source_rows = _entities(3)
        destination_rows = _entities(2)

        def source_read(args: list[str]):
            calls.append(args)
            if args[:2] == ["resource", "list"]:
                return [{"name": "corestore"}, {"name": "etsgwstate"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {"items": source_rows}
            raise AssertionError(args)

        def destination_read(args: list[str]):
            calls.append(args)
            if args[:2] == ["containerapp", "list"]:
                return [
                    {"name": "core", "min": 0, "max": 1},
                    {"name": "gateway", "min": 0, "max": 1},
                ]
            if args[:3] == ["containerapp", "replica", "list"]:
                return []
            if args[:2] == ["resource", "list"]:
                return [{"name": "corestore"}, {"name": "etsgwstate"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {"items": destination_rows}
            if args[:3] == ["storage", "file", "list"]:
                return [
                    {"name": "connector-runtime.db"},
                    {"name": "gateway-events.db"},
                    {"name": "gateway-sync.db"},
                ]
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "prefix.json"
            with patch.dict(os.environ, self.source_env, clear=True):
                with patch(
                    "scripts.azure_migration_prefix_preflight.az_json",
                    side_effect=source_read,
                ):
                    source = capture_source_manifest(manifest)
            self.assertEqual(source["source_next_index"], 3)

            with patch.dict(os.environ, self.destination_env, clear=True):
                with patch(
                    "scripts.azure_migration_prefix_preflight.az_json",
                    side_effect=destination_read,
                ):
                    result = verify_destination_prefix(manifest)

        self.assertEqual(result["source_next_index"], 3)
        self.assertEqual(result["destination_next_index"], 2)
        self.assertEqual(result["destination_entity_count"], 5)
        forbidden = {"create", "delete", "update", "set", "start", "stop", "restart"}
        self.assertFalse(any(call and call[0] in forbidden for call in calls))

    def test_verify_rejects_gateway_file_drift_with_actionable_diagnostic(self) -> None:
        source_state = _validated_state(_entities(2))
        manifest_payload = {
            "manifest_version": 1,
            "source_next_index": source_state["next_index"],
            "metadata_digest": source_state["metadata_digest"],
            "pair_digests": source_state["pair_digests"],
        }

        def destination_read(args: list[str]):
            if args[:2] == ["containerapp", "list"]:
                return [
                    {"name": "core", "min": 0, "max": 1},
                    {"name": "gateway", "min": 0, "max": 1},
                ]
            if args[:3] == ["containerapp", "replica", "list"]:
                return []
            if args[:2] == ["resource", "list"]:
                return [{"name": "corestore"}, {"name": "etsgwstate"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {"items": _entities(1)}
            if args[:3] == ["storage", "file", "list"]:
                return [
                    {"name": "connector-runtime.db"},
                    {"name": "gateway-events.db"},
                    {"name": "unexpected.db"},
                ]
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "prefix.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            with patch.dict(os.environ, self.destination_env, clear=True):
                with patch(
                    "scripts.azure_migration_prefix_preflight.az_json",
                    side_effect=destination_read,
                ):
                    with self.assertRaisesRegex(
                        MigrationControlError,
                        r"missing=gateway-sync\.db; unexpected=unexpected\.db",
                    ):
                        verify_destination_prefix(manifest)

    def test_verify_rejects_divergent_destination_prefix(self) -> None:
        source_state = _validated_state(_entities(2))
        manifest_payload = {
            "manifest_version": 1,
            "source_next_index": source_state["next_index"],
            "metadata_digest": source_state["metadata_digest"],
            "pair_digests": source_state["pair_digests"],
        }

        def destination_read(args: list[str]):
            if args[:2] == ["containerapp", "list"]:
                return [
                    {"name": "core", "min": 0, "max": 1},
                    {"name": "gateway", "min": 0, "max": 1},
                ]
            if args[:3] == ["containerapp", "replica", "list"]:
                return []
            if args[:2] == ["resource", "list"]:
                return [{"name": "corestore"}, {"name": "etsgwstate"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {"items": _entities(1, changed_hash_at=0)}
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "prefix.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            with patch.dict(os.environ, self.destination_env, clear=True):
                with patch(
                    "scripts.azure_migration_prefix_preflight.az_json",
                    side_effect=destination_read,
                ):
                    with self.assertRaisesRegex(MigrationControlError, "log_index=0"):
                        verify_destination_prefix(manifest)

    def test_verify_rejects_destination_ahead_of_source(self) -> None:
        source_state = _validated_state(_entities(1))
        manifest_payload = {
            "manifest_version": 1,
            "source_next_index": source_state["next_index"],
            "metadata_digest": source_state["metadata_digest"],
            "pair_digests": source_state["pair_digests"],
        }

        def destination_read(args: list[str]):
            if args[:2] == ["containerapp", "list"]:
                return [
                    {"name": "core", "min": 0, "max": 1},
                    {"name": "gateway", "min": 0, "max": 1},
                ]
            if args[:3] == ["containerapp", "replica", "list"]:
                return []
            if args[:2] == ["resource", "list"]:
                return [{"name": "corestore"}, {"name": "etsgwstate"}]
            if args[:3] == ["storage", "entity", "query"]:
                return {"items": _entities(2)}
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "prefix.json"
            manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
            with patch.dict(os.environ, self.destination_env, clear=True):
                with patch(
                    "scripts.azure_migration_prefix_preflight.az_json",
                    side_effect=destination_read,
                ):
                    with self.assertRaisesRegex(MigrationControlError, "exceeds"):
                        verify_destination_prefix(manifest)


if __name__ == "__main__":
    unittest.main()
