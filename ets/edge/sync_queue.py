"""Backward-compatible Edge facade for the shared synchronization queue.

The implementation moved to ``ets.runtime.sync_queue`` for GATE-G1 so ETS
Gateway and ETS Edge can consume the same durable queue without product-to-
product imports. Existing Edge import paths remain supported during migration.
"""

from ets.runtime.sync_queue import (
    QueueCapacityError,
    SyncConflictError,
    SyncQueue,
    SyncQueueStatus,
    SyncRecord,
    SyncState,
)

__all__ = [
    "QueueCapacityError",
    "SyncConflictError",
    "SyncQueue",
    "SyncQueueStatus",
    "SyncRecord",
    "SyncState",
]
