"""Immutable named profiles for ETS Core protocol behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from ets.core.errors import UnknownProfileError, VerificationOnlyProfileError


class ProfileKind(StrEnum):
    CANONICALIZATION = "canonicalization"
    HASH = "hash"
    MERKLE = "merkle"
    PROTOCOL = "protocol"
    SIGNATURE = "signature"


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    profile_id: str
    kind: ProfileKind
    algorithm: str
    version: int
    generation_allowed: bool = True
    description: str = ""


CANONICAL_JSON_V1 = ProtocolProfile(
    "ets.canonical.json.v1", ProfileKind.CANONICALIZATION, "canonical-json", 1
)
SHA256_V1 = ProtocolProfile("ets.hash.sha256.v1", ProfileKind.HASH, "sha256", 1)
RFC6962_MERKLE_V1 = ProtocolProfile(
    "ets.merkle.rfc6962-sha256.v1", ProfileKind.MERKLE, "rfc6962-sha256", 1
)
ALPHA_UNPREFIXED_MERKLE_V1 = ProtocolProfile(
    "ets.merkle.alpha-unprefixed-sha256.v1",
    ProfileKind.MERKLE,
    "alpha-unprefixed-sha256",
    1,
    generation_allowed=False,
    description="Legacy alpha verification-only profile.",
)
EVENT_RFC6962_V1 = ProtocolProfile(
    "ets.protocol.event.v1.rfc6962-sha256",
    ProfileKind.PROTOCOL,
    "evidence-event-v1+rfc6962-sha256",
    1,
)
EVENT_ALPHA_UNPREFIXED_V1 = ProtocolProfile(
    "ets.protocol.event.v1.alpha-unprefixed",
    ProfileKind.PROTOCOL,
    "evidence-event-v1+alpha-unprefixed-sha256",
    1,
    generation_allowed=False,
    description="Legacy alpha verification-only protocol profile.",
)
ED25519_V1 = ProtocolProfile("ets.signature.ed25519.v1", ProfileKind.SIGNATURE, "ed25519", 1)

_PROFILE_VALUES = (
    CANONICAL_JSON_V1,
    SHA256_V1,
    RFC6962_MERKLE_V1,
    ALPHA_UNPREFIXED_MERKLE_V1,
    EVENT_RFC6962_V1,
    EVENT_ALPHA_UNPREFIXED_V1,
    ED25519_V1,
)
PROFILES: Mapping[str, ProtocolProfile] = MappingProxyType(
    {profile.profile_id: profile for profile in _PROFILE_VALUES}
)


def resolve_profile(profile_id: str, *, for_generation: bool = False) -> ProtocolProfile:
    try:
        profile = PROFILES[profile_id]
    except KeyError as exc:
        raise UnknownProfileError(f"Unknown ETS profile: {profile_id}") from exc
    if for_generation and not profile.generation_allowed:
        raise VerificationOnlyProfileError(
            f"Profile is verification-only and cannot generate new artifacts: {profile_id}"
        )
    return profile
