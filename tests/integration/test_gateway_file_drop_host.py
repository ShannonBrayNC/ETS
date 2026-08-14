from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

import pytest

import ets.gateway.file_drop_host as file_drop_module
from ets.core.api import InMemoryAppendOnlyLog
from ets.gateway.file_drop_host import (
    GatewayFileDropHost,
    GatewayFileDropHostSaturatedError,
    GatewayFileDropPolicy,
    GatewayFileDropShuttingDownError,
    GatewayFileDropSubmission,
)
from ets.gateway.file_ingress import GatewayFileIngressService
from ets.gateway.source_registry import SourceRegistration, StaticSourceRegistry
from ets.runtime.sync_queue import QueueCapacityError, SyncQueue, SyncRecord

PRINCIPAL = "spiffe://example.test/workload/file-drop"


class FailOnceQueue(SyncQueue):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_next = True

    def enqueue(self, payload: dict[str, Any]) -> SyncRecord:
        if self.fail_next:
            self.fail_next = False
            raise QueueCapacityError("simulated queue race")
        return super().enqueue(payload)


def registration() -> SourceRegistration:
    return SourceRegistration(
        principal=PRINCIPAL,
        source_id="file-drop-a",
        source_system="filesystem",
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        adapter_id="gateway-file",
        adapter_version="1.0",
        event_type="file.observed",
        classification="internal",
        redaction_profile="file-metadata-v1",
        minimization_profile="file-digest-metadata-v1",
        clock_quality="synchronized",
    )


def make_host(
    tmp_path: Path,
    *,
    policy: GatewayFileDropPolicy | None = None,
    queue: SyncQueue | None = None,
) -> tuple[GatewayFileDropHost, InMemoryAppendOnlyLog, SyncQueue, Path]:
    intake_root = tmp_path / "drop"
    intake_root.mkdir()
    event_log = InMemoryAppendOnlyLog()
    sync_queue = queue or SyncQueue(tmp_path / "sync.db")
    registry = StaticSourceRegistry([registration()])
    service = GatewayFileIngressService(
        registry=registry,
        event_log=event_log,
        sync_queue=sync_queue,
    )
    host = GatewayFileDropHost(
        service=service,
        registry=registry,
        intake_root=intake_root,
        policy=policy,
    )
    return host, event_log, sync_queue, intake_root


def test_file_drop_valid_empty_exact_and_over_bound(tmp_path: Path) -> None:
    async def scenario() -> None:
        policy = GatewayFileDropPolicy(max_object_bytes=8, read_chunk_bytes=4)
        host, event_log, _, root = make_host(tmp_path, policy=policy)
        (root / "valid.bin").write_bytes(b"ets")
        (root / "empty.bin").write_bytes(b"")
        (root / "exact.bin").write_bytes(b"12345678")
        (root / "over.bin").write_bytes(b"123456789")

        valid = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="valid.bin", delivery_id="valid"),
        )
        empty = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="empty.bin", delivery_id="empty"),
        )
        exact = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="exact.bin", delivery_id="exact"),
        )
        over = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="over.bin", delivery_id="over"),
        )

        assert valid.stage == empty.stage == exact.stage == "sync_queued"
        assert over.stage == "rejected"
        assert over.error_code == "filesystem_rejected"
        assert len(event_log.list_entries()) == 3

    asyncio.run(scenario())


def test_file_drop_authorization_fails_before_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        host, event_log, _, root = make_host(tmp_path)
        (root / "secret.bin").write_bytes(b"do-not-read")
        called = False

        def forbidden_digest(*args: Any, **kwargs: Any) -> Any:
            nonlocal called
            called = True
            raise AssertionError("unauthorized submission reached filesystem read")

        monkeypatch.setattr(file_drop_module, "digest_filesystem_object", forbidden_digest)
        result = await host.submit(
            "spiffe://example.test/workload/unauthorized",
            GatewayFileDropSubmission(relative_path="secret.bin", delivery_id="unauthorized"),
        )

        assert result.stage == "rejected"
        assert result.error_code == "source_unauthorized"
        assert called is False
        assert event_log.list_entries() == []

    asyncio.run(scenario())


def test_file_drop_traversal_and_symlink_escape_fail_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        host, event_log, _, root = make_host(tmp_path)
        outside = tmp_path / "outside.bin"
        outside.write_bytes(b"outside")
        link = root / "link.bin"
        link.symlink_to(outside)

        traversal = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="../outside.bin", delivery_id="traversal"),
        )
        linked = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="link.bin", delivery_id="link"),
        )

        assert traversal.stage == "rejected"
        assert traversal.error_code == "filesystem_rejected"
        assert linked.stage == "rejected"
        assert linked.error_code == "filesystem_rejected"
        assert event_log.list_entries() == []

    asyncio.run(scenario())


def test_file_drop_retry_and_conflict_are_truthful(tmp_path: Path) -> None:
    async def scenario() -> None:
        host, event_log, sync_queue, root = make_host(tmp_path)
        path = root / "retry.bin"
        path.write_bytes(b"first")
        submission = GatewayFileDropSubmission(
            relative_path="retry.bin",
            delivery_id="retry-1",
        )

        first = await host.submit(PRINCIPAL, submission)
        retry = await host.submit(PRINCIPAL, submission)
        path.write_bytes(b"different")
        conflict = await host.submit(PRINCIPAL, submission)

        assert first.stage == "sync_queued"
        assert first.duplicate is False
        assert retry.stage == "sync_queued"
        assert retry.duplicate is True
        assert conflict.stage == "rejected"
        assert conflict.error_code == "conflict"
        assert len(event_log.list_entries()) == 1
        assert sync_queue.status().queue_depth == 1

    asyncio.run(scenario())


def test_file_drop_partial_commit_status_recovers_on_retry(tmp_path: Path) -> None:
    async def scenario() -> None:
        queue = FailOnceQueue(tmp_path / "race.db")
        host, event_log, sync_queue, root = make_host(tmp_path, queue=queue)
        (root / "partial.bin").write_bytes(b"payload")
        submission = GatewayFileDropSubmission(
            relative_path="partial.bin",
            delivery_id="partial",
        )

        partial = await host.submit(PRINCIPAL, submission)
        retry = await host.submit(PRINCIPAL, submission)

        assert partial.stage == "partial_commit"
        assert partial.committed_local is True
        assert partial.sync_queued is False
        assert retry.stage == "sync_queued"
        assert retry.duplicate is True
        assert len(event_log.list_entries()) == 1
        assert sync_queue.status().queue_depth == 1

    asyncio.run(scenario())


def test_file_drop_raw_marker_absent_from_status_event_and_sync(tmp_path: Path) -> None:
    async def scenario() -> None:
        marker = "RAW-FILE-HOST-MARKER"
        host, event_log, sync_queue, root = make_host(tmp_path)
        (root / "marker.bin").write_text(marker, encoding="utf-8")
        result = await host.submit(
            PRINCIPAL,
            GatewayFileDropSubmission(relative_path="marker.bin", delivery_id="marker"),
        )

        assert marker not in repr(result)
        event_dump = json.dumps(event_log.list_entries()[0].event.model_dump(mode="json"))
        assert marker not in event_dump
        queued = sync_queue.claim_batch(1)
        assert len(queued) == 1
        assert marker not in json.dumps(queued[0].payload)

    asyncio.run(scenario())


def test_file_drop_concurrency_saturation_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        started = threading.Event()
        release = threading.Event()
        original = file_drop_module.digest_filesystem_object

        def slow_digest(*args: Any, **kwargs: Any) -> Any:
            started.set()
            release.wait(timeout=2)
            return original(*args, **kwargs)

        monkeypatch.setattr(file_drop_module, "digest_filesystem_object", slow_digest)
        policy = GatewayFileDropPolicy(
            max_concurrent_submissions=1,
            admission_timeout_seconds=0.01,
        )
        host, _, _, root = make_host(tmp_path, policy=policy)
        (root / "one.bin").write_bytes(b"one")
        (root / "two.bin").write_bytes(b"two")

        first = asyncio.create_task(
            host.submit(
                PRINCIPAL,
                GatewayFileDropSubmission(relative_path="one.bin", delivery_id="one"),
            )
        )
        assert await asyncio.to_thread(started.wait, 1)
        with pytest.raises(GatewayFileDropHostSaturatedError):
            await host.submit(
                PRINCIPAL,
                GatewayFileDropSubmission(relative_path="two.bin", delivery_id="two"),
            )
        release.set()
        assert (await first).stage == "sync_queued"

    asyncio.run(scenario())


def test_file_drop_shutdown_drains_admitted_work_and_rejects_new(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        started = threading.Event()
        release = threading.Event()
        original = file_drop_module.digest_filesystem_object

        def slow_digest(*args: Any, **kwargs: Any) -> Any:
            started.set()
            release.wait(timeout=2)
            return original(*args, **kwargs)

        monkeypatch.setattr(file_drop_module, "digest_filesystem_object", slow_digest)
        policy = GatewayFileDropPolicy(graceful_shutdown_seconds=1.0)
        host, event_log, _, root = make_host(tmp_path, policy=policy)
        (root / "admitted.bin").write_bytes(b"admitted")
        (root / "new.bin").write_bytes(b"new")

        admitted = asyncio.create_task(
            host.submit(
                PRINCIPAL,
                GatewayFileDropSubmission(
                    relative_path="admitted.bin",
                    delivery_id="admitted",
                ),
            )
        )
        assert await asyncio.to_thread(started.wait, 1)
        shutdown = asyncio.create_task(host.shutdown())
        await asyncio.sleep(0)
        assert host.accepting is False
        with pytest.raises(GatewayFileDropShuttingDownError):
            await host.submit(
                PRINCIPAL,
                GatewayFileDropSubmission(relative_path="new.bin", delivery_id="new"),
            )

        release.set()
        result = await admitted
        await shutdown
        assert result.stage == "sync_queued"
        assert host.drain_timed_out is False
        assert len(event_log.list_entries()) == 1

    asyncio.run(scenario())
