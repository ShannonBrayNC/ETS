"""Concrete bounded explicit-submission file/drop host for ETS Gateway G1E-D."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ets.capture import FilesystemObjectError, StreamDigestError, digest_filesystem_object
from ets.gateway.file_capture import GatewayFileCaptureError, GatewayFileCaptureRequest
from ets.gateway.file_ingress import GatewayFileIngressService
from ets.gateway.ingress import (
    GatewayBackpressureError,
    GatewayConflictError,
    GatewayIngressError,
    GatewayIngressReceipt,
    GatewayPartialCommitError,
)
from ets.gateway.source_registry import SourceAuthorizationError, StaticSourceRegistry

FileSubmissionStage = Literal[
    "discovered",
    "reading",
    "rejected",
    "committed_local",
    "sync_queued",
    "partial_commit",
]
FileSubmissionErrorCode = Literal[
    "backpressure",
    "capture_rejected",
    "conflict",
    "filesystem_rejected",
    "shutdown_timeout",
    "source_unauthorized",
]


class GatewayFileDropHostError(RuntimeError):
    """Base error for file/drop host lifecycle and admission failures."""


class GatewayFileDropHostSaturatedError(GatewayFileDropHostError):
    """Raised when bounded submission admission is exhausted."""


class GatewayFileDropShuttingDownError(GatewayFileDropHostError):
    """Raised when new submissions arrive after shutdown has begun."""


@dataclass(frozen=True, slots=True)
class GatewayFileDropPolicy:
    """Bounded host policy for explicit file/drop submissions."""

    max_concurrent_submissions: int = 8
    admission_timeout_seconds: float = 0.05
    max_object_bytes: int = 64 * 1024 * 1024
    read_chunk_bytes: int = 64 * 1024
    graceful_shutdown_seconds: float = 30.0
    max_status_entries: int = 1024

    def __post_init__(self) -> None:
        integer_limits = (
            self.max_concurrent_submissions,
            self.max_object_bytes,
            self.read_chunk_bytes,
            self.max_status_entries,
        )
        if any(value < 1 for value in integer_limits):
            raise ValueError("Gateway file/drop integer limits must be positive")
        if self.admission_timeout_seconds <= 0 or self.graceful_shutdown_seconds <= 0:
            raise ValueError("Gateway file/drop time limits must be positive")
        if self.read_chunk_bytes > self.max_object_bytes:
            raise ValueError("read_chunk_bytes cannot exceed max_object_bytes")


@dataclass(frozen=True, slots=True)
class GatewayFileDropSubmission:
    """One explicit file/drop submission independent of watcher discovery semantics."""

    relative_path: str
    delivery_id: str
    declared_filename: str | None = None
    declared_content_type: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not 1 <= len(self.delivery_id) <= 200:
            raise ValueError("delivery_id must be 1-200 characters")
        if (
            self.declared_filename is not None
            and not 1 <= len(self.declared_filename) <= 500
        ):
            raise ValueError("declared_filename must be 1-500 characters when supplied")
        if (
            self.declared_content_type is not None
            and not 1 <= len(self.declared_content_type) <= 200
        ):
            raise ValueError("declared_content_type must be 1-200 characters when supplied")
        if (
            self.correlation_id is not None
            and not 1 <= len(self.correlation_id) <= 200
        ):
            raise ValueError("correlation_id must be 1-200 characters when supplied")


@dataclass(frozen=True, slots=True)
class GatewayFileSubmissionStatus:
    """Bounded operational status that never contains raw file content."""

    delivery_id: str
    relative_path: str
    stage: FileSubmissionStage
    committed_local: bool = False
    sync_queued: bool = False
    duplicate: bool = False
    event_id: str | None = None
    error_code: FileSubmissionErrorCode | None = None

    def __post_init__(self) -> None:
        if self.sync_queued and not self.committed_local:
            raise ValueError("sync_queued requires committed_local")
        if self.stage == "sync_queued" and not (self.committed_local and self.sync_queued):
            raise ValueError("sync_queued stage requires committed and queued state")
        if self.stage == "committed_local" and not self.committed_local:
            raise ValueError("committed_local stage requires committed state")
        if self.stage == "partial_commit" and not self.committed_local:
            raise ValueError("partial_commit stage requires committed state")
        if self.stage == "rejected" and self.error_code is None:
            raise ValueError("rejected stage requires an error code")
        if self.stage != "rejected" and self.error_code is not None:
            raise ValueError("only rejected status may carry an error code")


class GatewayFileDropHost:
    """Bounded explicit-submission host around G1E-B and G1E-C."""

    def __init__(
        self,
        *,
        service: GatewayFileIngressService,
        registry: StaticSourceRegistry,
        intake_root: str | Path,
        policy: GatewayFileDropPolicy | None = None,
    ) -> None:
        self.service = service
        self.registry = registry
        self.intake_root = Path(intake_root)
        self.policy = policy or GatewayFileDropPolicy()
        self._accepting = True
        self._semaphore = asyncio.Semaphore(self.policy.max_concurrent_submissions)
        self._active_tasks: set[asyncio.Task[object]] = set()
        self._drained = asyncio.Event()
        self._drained.set()
        self._statuses: OrderedDict[str, GatewayFileSubmissionStatus] = OrderedDict()
        self.drain_timed_out = False

    @property
    def accepting(self) -> bool:
        """Return whether new explicit submissions may be admitted."""

        return self._accepting

    @property
    def active_submissions(self) -> int:
        """Return the number of currently admitted submission tasks."""

        return len(self._active_tasks)

    def status(self, delivery_id: str) -> GatewayFileSubmissionStatus | None:
        """Return the latest bounded operational status for one delivery identity."""

        return self._statuses.get(delivery_id)

    async def submit(
        self,
        principal: str,
        submission: GatewayFileDropSubmission,
    ) -> GatewayFileSubmissionStatus:
        """Resolve, hash, and commit one explicitly submitted file/drop object."""

        if not self._accepting:
            raise GatewayFileDropShuttingDownError("Gateway file/drop host is shutting down")

        acquired = False
        task = asyncio.current_task()
        try:
            try:
                async with asyncio.timeout(self.policy.admission_timeout_seconds):
                    await self._semaphore.acquire()
                acquired = True
            except TimeoutError as exc:
                raise GatewayFileDropHostSaturatedError(
                    "Gateway file/drop submission concurrency is saturated"
                ) from exc

            if not self._accepting:
                raise GatewayFileDropShuttingDownError(
                    "Gateway file/drop host is shutting down"
                )

            try:
                self.registry.resolve(principal)
            except SourceAuthorizationError:
                return self._rejected(submission, "source_unauthorized")

            if task is not None:
                if not self._active_tasks:
                    self._drained.clear()
                self._active_tasks.add(task)

            self._record(
                GatewayFileSubmissionStatus(
                    delivery_id=submission.delivery_id,
                    relative_path=submission.relative_path,
                    stage="discovered",
                )
            )
            self._record(
                GatewayFileSubmissionStatus(
                    delivery_id=submission.delivery_id,
                    relative_path=submission.relative_path,
                    stage="reading",
                )
            )

            observation = await asyncio.to_thread(
                digest_filesystem_object,
                self.intake_root,
                submission.relative_path,
                maximum_bytes=self.policy.max_object_bytes,
                chunk_size=self.policy.read_chunk_bytes,
            )
            capture_request = GatewayFileCaptureRequest(
                observation=observation,
                delivery_id=submission.delivery_id,
                declared_filename=submission.declared_filename,
                declared_content_type=submission.declared_content_type,
                correlation_id=submission.correlation_id,
            )
            receipt = self.service.ingest_file(principal, capture_request)
            status = _status_from_receipt(submission, receipt)
            self._record(status)
            return status
        except asyncio.CancelledError:
            self._rejected(submission, "shutdown_timeout")
            raise
        except GatewayPartialCommitError as exc:
            status = GatewayFileSubmissionStatus(
                delivery_id=submission.delivery_id,
                relative_path=submission.relative_path,
                stage="partial_commit",
                committed_local=True,
                sync_queued=False,
                duplicate=exc.receipt.duplicate,
                event_id=exc.receipt.event_id,
            )
            self._record(status)
            return status
        except GatewayBackpressureError:
            return self._rejected(submission, "backpressure")
        except GatewayConflictError:
            return self._rejected(submission, "conflict")
        except (FilesystemObjectError, StreamDigestError):
            return self._rejected(submission, "filesystem_rejected")
        except (GatewayFileCaptureError, GatewayIngressError):
            return self._rejected(submission, "capture_rejected")
        finally:
            if task is not None and task in self._active_tasks:
                self._active_tasks.discard(task)
                if not self._active_tasks:
                    self._drained.set()
            if acquired:
                self._semaphore.release()

    async def shutdown(self) -> None:
        """Reject new submissions and drain admitted work within the bounded grace window."""

        self._accepting = False
        if not self._active_tasks:
            return
        try:
            async with asyncio.timeout(self.policy.graceful_shutdown_seconds):
                await self._drained.wait()
        except TimeoutError:
            self.drain_timed_out = True
            tasks = tuple(self._active_tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    def _rejected(
        self,
        submission: GatewayFileDropSubmission,
        error_code: FileSubmissionErrorCode,
    ) -> GatewayFileSubmissionStatus:
        status = GatewayFileSubmissionStatus(
            delivery_id=submission.delivery_id,
            relative_path=submission.relative_path,
            stage="rejected",
            error_code=error_code,
        )
        self._record(status)
        return status

    def _record(self, status: GatewayFileSubmissionStatus) -> None:
        self._statuses[status.delivery_id] = status
        self._statuses.move_to_end(status.delivery_id)
        while len(self._statuses) > self.policy.max_status_entries:
            self._statuses.popitem(last=False)


def _status_from_receipt(
    submission: GatewayFileDropSubmission,
    receipt: GatewayIngressReceipt,
) -> GatewayFileSubmissionStatus:
    stage: FileSubmissionStage = "sync_queued" if receipt.sync_queued else "committed_local"
    return GatewayFileSubmissionStatus(
        delivery_id=submission.delivery_id,
        relative_path=submission.relative_path,
        stage=stage,
        committed_local=receipt.committed_local,
        sync_queued=receipt.sync_queued,
        duplicate=receipt.duplicate,
        event_id=receipt.event_id,
    )
