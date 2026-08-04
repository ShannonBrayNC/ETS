"""
ETS Core protocol profile registry.

This module defines immutable protocol profiles and provides lookup helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from ets.core.errors import (
    UnknownProfileError,
    VerificationOnlyProfileError,
)


class ProfileKind(StrEnum):
    CANONICALIZATION = "canonicalization"
    HASH = "hash"
    MERKLE = "merkle"
    EVENT = "event"
    SIGNATURE = "signature"


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    id: str
    kind: ProfileKind
    version: str
    production: bool = True
    verification_only: bool = False
    description: str = ""


# ----------------------------------------------------------------------
# Canonical profiles
# ----------------------------------------------------------------------

CANONICAL_JSON_V1 = ProtocolProfile(
    id="ets.canonical.json.v1",
    kind=ProfileKind.CANONICALIZATION,
    version="1",
    description="Canonical JSON serialization profile",
)

SHA256_V1 = ProtocolProfile(
    id="ets.hash.sha256.v1",
    kind=ProfileKind.HASH,
    version="1",
    description="SHA-256 hash profile",
)

RFC6962_MERKLE_V1 = ProtocolProfile(
    id="ets.merkle.rfc6962-sha256.v1",
    kind=ProfileKind.MERKLE,
    version="1",
    description="RFC6962 Merkle profile",
)

ALPHA_UNPREFIXED_MERKLE_V1 = ProtocolProfile(
    id="ets.merkle.alpha-unprefixed-sha256.v1",
    kind=ProfileKind.MERKLE,
    version="1",
    production=False,
    verification_only=True,
    description="Legacy alpha verification profile",
)

EVENT_RFC6962_V1 = ProtocolProfile(
    id="ets.protocol.event.v1.rfc6962-sha256",
    kind=ProfileKind.EVENT,
    version="1",
    description="Current ETS event profile",
)

EVENT_ALPHA_UNPREFIXED_V1 = ProtocolProfile(
    id="ets.protocol.event.v1.alpha-unprefixed",
    kind=ProfileKind.EVENT,
    version="1",
    production=False,
    verification_only=True,
    description="Legacy alpha event profile",
)

ED25519_V1 = ProtocolProfile(
    id="ets.signature.ed25519.v1",
    kind=ProfileKind.SIGNATURE,
    version="1",
    description="Ed25519 signature profile",
)

# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------

_PROFILES = {
    profile.id: profile
    for profile in (
        CANONICAL_JSON_V1,
        SHA256_V1,
        RFC6962_MERKLE_V1,
        ALPHA_UNPREFIXED_MERKLE_V1,
        EVENT_RFC6962_V1,
        EVENT_ALPHA_UNPREFIXED_V1,
        ED25519_V1,
    )
}

PROFILES: Mapping[str, ProtocolProfile] = MappingProxyType(_PROFILES)


def resolve_profile(
    profile_id: str,
    *,
    allow_verification_only: bool = True,
) -> ProtocolProfile:
    """
    Resolve a registered protocol profile.

    Raises:
        UnknownProfileError
        VerificationOnlyProfileError
    """
    try:
        profile = PROFILES[profile_id]
    except KeyError as exc:
        raise UnknownProfileError(profile_id) from exc

    if profile.verification_only and not allow_verification_only:
        raise VerificationOnlyProfileError(profile.id)

    return profile


def list_profiles(
    *,
    production: bool | None = None,
    verification: bool | None = None,
) -> tuple[ProtocolProfile, ...]:
    """
    Return registered profiles in stable identifier order.
    """
    profiles = sorted(PROFILES.values(), key=lambda p: p.id)

    if production is not None:
        profiles = [p for p in profiles if p.production is production]

    if verification is not None:
        profiles = [
            p
            for p in profiles
            if p.verification_only is verification
        ]

    return tuple(profiles)


__all__ = [
    "ProfileKind",
    "ProtocolProfile",
    "CANONICAL_JSON_V1",
    "SHA256_V1",
    "RFC6962_MERKLE_V1",
    "ALPHA_UNPREFIXED_MERKLE_V1",
    "EVENT_RFC6962_V1",
    "EVENT_ALPHA_UNPREFIXED_V1",
    "ED25519_V1",
    "PROFILES",
    "resolve_profile",
    "list_profiles",
]
