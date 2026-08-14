"""Server-controlled authorization roles and capabilities for ETS operator surfaces."""

from __future__ import annotations

from typing import Any, Literal

AuthRole = Literal[
    "viewer",
    "evidence_producer",
    "operator",
    "auditor",
    "administrator",
]
AuthCapability = Literal[
    "evidence.read",
    "evidence.create",
    "evidence.verify",
    "evidence.export",
    "connector.read",
    "connector.manage",
    "audit.read",
    "admin.read",
    "admin.manage",
]
AuthorizationProfile = Literal["local_nonproduction", "production"]


class AuthRoleError(ValueError):
    """Raised when a signed role claim cannot map to the ETS authorization model."""


ROLE_CAPABILITIES: dict[AuthRole, frozenset[AuthCapability]] = {
    "viewer": frozenset({"evidence.read"}),
    "evidence_producer": frozenset(
        {
            "evidence.read",
            "evidence.create",
            "evidence.verify",
            "evidence.export",
        }
    ),
    "operator": frozenset(
        {
            "evidence.read",
            "evidence.create",
            "evidence.verify",
            "evidence.export",
            "connector.read",
            "connector.manage",
        }
    ),
    "auditor": frozenset(
        {
            "evidence.read",
            "evidence.verify",
            "evidence.export",
            "connector.read",
            "audit.read",
        }
    ),
    "administrator": frozenset(
        {
            "evidence.read",
            "evidence.create",
            "evidence.verify",
            "evidence.export",
            "connector.read",
            "connector.manage",
            "audit.read",
            "admin.read",
            "admin.manage",
        }
    ),
}
ALL_CAPABILITIES: tuple[AuthCapability, ...] = tuple(
    sorted({capability for values in ROLE_CAPABILITIES.values() for capability in values})
)


def parse_role_claim(value: Any) -> tuple[AuthRole, ...]:
    """Validate signed role claims; arbitrary client-defined capabilities are never accepted."""

    if value is None:
        return ()
    raw_roles: list[Any]
    if isinstance(value, str):
        raw_roles = [value]
    elif isinstance(value, list):
        raw_roles = value
    else:
        raise AuthRoleError("bearer token roles claim must be a string or list of strings")

    roles: list[AuthRole] = []
    for item in raw_roles:
        if not isinstance(item, str) or item not in ROLE_CAPABILITIES:
            raise AuthRoleError("bearer token contains an unsupported ETS role")
        role = item
        if role not in roles:
            roles.append(role)
    return tuple(sorted(roles))


def capabilities_for_roles(roles: tuple[AuthRole, ...]) -> tuple[AuthCapability, ...]:
    """Derive capabilities exclusively from the server-controlled ETS role map."""

    return tuple(sorted({capability for role in roles for capability in ROLE_CAPABILITIES[role]}))
