"""Gateway runtime composition helpers for GATE-G1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ets.runtime.sync_queue import SyncQueue


@dataclass(frozen=True, slots=True)
class GatewayRuntimeConfig:
    """Minimal local-runtime configuration for the first Gateway slice."""

    sync_db: Path
    sync_max_items: int = 10_000
    sync_max_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.sync_max_items < 1:
            raise ValueError("sync_max_items must be positive")
        if self.sync_max_bytes < 1:
            raise ValueError("sync_max_bytes must be positive")


def open_sync_queue(config: GatewayRuntimeConfig) -> SyncQueue:
    """Open the shared durable synchronization queue for a Gateway runtime."""

    return SyncQueue(
        config.sync_db,
        max_items=config.sync_max_items,
        max_bytes=config.sync_max_bytes,
    )
