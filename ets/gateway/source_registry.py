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
        required = {
            "principal": self.principal,
            "source_id": self.source_id,
            "source_system": self.source_system,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "adapter_id": self.adapter_id,
            "event_type": self.event_type,
        }
        empty = [name for name, value in required.items() if not value]
        if empty:
            raise ValueError(f"source registration requires: {', '.join(sorted(empty))}")


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
