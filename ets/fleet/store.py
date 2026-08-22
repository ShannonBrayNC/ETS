"""Storage boundary for ETS Fleet enrollment state."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from threading import RLock
from typing import Protocol

from ets.fleet.models import DeviceEnrollmentRecord, RotationWindow


class EnrollmentStoreConflict(RuntimeError):
    """An authoritative Fleet write conflicted with concurrent retained state."""


class EnrollmentStore(Protocol):
    """Provider-neutral authoritative Fleet enrollment persistence boundary.

    ``transaction`` is intentionally part of the contract so a production shared
    store can bind one complete ``DeviceEnrollmentService`` lifecycle operation to
    a database transaction. Local profiles retain the same semantics through the
    in-memory re-entrant lock.
    """

    def transaction(self) -> AbstractContextManager[None]: ...
    def get_enrollment(self, enrollment_id: str) -> DeviceEnrollmentRecord | None: ...
    def put_enrollment(self, record: DeviceEnrollmentRecord) -> None: ...
    def get_current_enrollment_id(self, device_id: str) -> str | None: ...
    def set_current_enrollment_id(self, device_id: str, enrollment_id: str) -> None: ...
    def get_public_identity_owner(self, fingerprint: str) -> str | None: ...
    def set_public_identity_owner(self, fingerprint: str, device_id: str) -> None: ...
    def get_rotation(self, device_id: str) -> RotationWindow | None: ...
    def set_rotation(self, rotation: RotationWindow) -> None: ...
    def clear_rotation(self, device_id: str) -> None: ...


class InMemoryEnrollmentStore:
    """Thread-safe deterministic reference store for tests and local profiles."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._enrollments: dict[str, DeviceEnrollmentRecord] = {}
        self._current: dict[str, str] = {}
        self._identity_owner: dict[str, str] = {}
        self._rotations: dict[str, RotationWindow] = {}

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Serialize one complete local lifecycle operation.

        The lock is re-entrant because credential rotation invokes activation as a
        nested lifecycle operation. PostgreSQL C3B supplies the same nesting
        behavior with one shared SERIALIZABLE transaction per outer operation.
        """

        with self._lock:
            yield

    def get_enrollment(self, enrollment_id: str) -> DeviceEnrollmentRecord | None:
        with self._lock:
            return self._enrollments.get(enrollment_id)

    def put_enrollment(self, record: DeviceEnrollmentRecord) -> None:
        with self._lock:
            self._enrollments[record.enrollment_id] = record

    def get_current_enrollment_id(self, device_id: str) -> str | None:
        with self._lock:
            return self._current.get(device_id)

    def set_current_enrollment_id(self, device_id: str, enrollment_id: str) -> None:
        with self._lock:
            self._current[device_id] = enrollment_id

    def list_current_enrollments(self) -> list[DeviceEnrollmentRecord]:
        """Return a stable snapshot of current device enrollments for read-side views."""

        with self._lock:
            enrollment_ids = tuple(self._current.values())
            records = [
                self._enrollments[enrollment_id]
                for enrollment_id in enrollment_ids
                if enrollment_id in self._enrollments
            ]
        return sorted(records, key=lambda item: item.device_id)

    def get_public_identity_owner(self, fingerprint: str) -> str | None:
        with self._lock:
            return self._identity_owner.get(fingerprint)

    def set_public_identity_owner(self, fingerprint: str, device_id: str) -> None:
        with self._lock:
            self._identity_owner[fingerprint] = device_id

    def get_rotation(self, device_id: str) -> RotationWindow | None:
        with self._lock:
            return self._rotations.get(device_id)

    def set_rotation(self, rotation: RotationWindow) -> None:
        with self._lock:
            self._rotations[rotation.device_id] = rotation

    def clear_rotation(self, device_id: str) -> None:
        with self._lock:
            self._rotations.pop(device_id, None)
