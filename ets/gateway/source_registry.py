"""Server-authorized source registrations for ETS Gateway ingress."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

ClockQuality = Literal["synchronized", "estimated", "degraded", "unknown"]


class SourceAuthorizationError(PermissionError):
    """Raised when an authenticated principal has no enabled source registration."""


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    """Authoritative Gateway scope and capture policy for one source principal."""

    principal: str
    source_id: str
    source_system: str
    tenant_id: str
    workspace_id: str
    adapter_id: str
    event_type: str
    adapter_version: str | None = None
    classification: str | None = None
    redaction_profile: str | None = None
    minimization_profile: str | None = None
    redacted_keys: frozenset[str] = frozenset()
    clock_quality: ClockQuality = "unknown"
    enabled: bool = True

    def __post_init__(self) -> None:
        _bounded("principal", self.principal, 500)
        _bounded("source_id", self.source_id, 500)
        _bounded("source_system", self.source_system, 200)
        _bounded("tenant_id", self.tenant_id, 128)
        _bounded("workspace_id", self.workspace_id, 128)
        _bounded("adapter_id", self.adapter_id, 200)
        _bounded("event_type", self.event_type, 128)
        _bounded_optional("adapter_version", self.adapter_version, 100)
        _bounded_optional("classification", self.classification, 100)
        _bounded_optional("redaction_profile", self.redaction_profile, 100)
        _bounded_optional("minimization_profile", self.minimization_profile, 100)
        if any(not key or len(key) > 200 for key in self.redacted_keys):
            raise ValueError("redacted_keys must contain non-empty keys up to 200 characters")


class StaticSourceRegistry:
    """Immutable in-memory source authorization map for the first Gateway slice."""

    def __init__(self, registrations: Iterable[SourceRegistration]) -> None:
        by_principal: dict[str, SourceRegistration] = {}
        for registration in registrations:
            if registration.principal in by_principal:
                raise ValueError(
                    f"duplicate source principal registration: {registration.principal}"
                )
            by_principal[registration.principal] = registration
        self._by_principal = by_principal

    def resolve(self, principal: str) -> SourceRegistration:
        """Resolve authoritative scope from the authenticated transport principal."""

        registration = self._by_principal.get(principal)
        if registration is None or not registration.enabled:
            raise SourceAuthorizationError("source principal is not authorized")
        return registration


def _bounded(name: str, value: str, maximum: int) -> None:
    if not 1 <= len(value) <= maximum:
        raise ValueError(f"{name} must be 1-{maximum} characters")


def _bounded_optional(name: str, value: str | None, maximum: int) -> None:
    if value is not None:
        _bounded(name, value, maximum)
