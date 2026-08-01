"""Contract tests for the ETS Core protocol profile registry."""

import pytest

from ets.core.errors import UnknownProfileError, VerificationOnlyProfileError
from ets.core.profiles import (
    ALPHA_UNPREFIXED_MERKLE_V1,
    EVENT_ALPHA_UNPREFIXED_V1,
    EVENT_RFC6962_V1,
    PROFILES,
    RFC6962_MERKLE_V1,
    ProtocolProfile,
    list_profiles,
    resolve_profile,
)


def test_registry_is_immutable() -> None:
    with pytest.raises(TypeError):
        PROFILES["example"] = RFC6962_MERKLE_V1  # type: ignore[index]


def test_profile_identifiers_are_unique_and_sorted() -> None:
    identifiers = tuple(PROFILES)
    assert len(identifiers) == len(set(identifiers))
    assert tuple(profile.id for profile in list_profiles()) == tuple(sorted(identifiers))


def test_resolve_active_rfc6962_profiles() -> None:
    assert resolve_profile(RFC6962_MERKLE_V1.id) is RFC6962_MERKLE_V1
    assert resolve_profile(EVENT_RFC6962_V1.id) is EVENT_RFC6962_V1
    assert RFC6962_MERKLE_V1.production is True
    assert RFC6962_MERKLE_V1.verification_only is False


def test_legacy_profiles_are_verification_only() -> None:
    assert ALPHA_UNPREFIXED_MERKLE_V1.verification_only is True
    assert EVENT_ALPHA_UNPREFIXED_V1.verification_only is True
    assert resolve_profile(ALPHA_UNPREFIXED_MERKLE_V1.id) is ALPHA_UNPREFIXED_MERKLE_V1

    with pytest.raises(VerificationOnlyProfileError):
        resolve_profile(
            ALPHA_UNPREFIXED_MERKLE_V1.id,
            allow_verification_only=False,
        )


def test_unknown_profile_fails_deterministically() -> None:
    with pytest.raises(UnknownProfileError) as exc_info:
        resolve_profile("ets.profile.unknown")

    assert "ets.profile.unknown" in str(exc_info.value)


def test_filters_return_only_matching_profiles() -> None:
    production_profiles = list_profiles(production=True)
    legacy_profiles = list_profiles(verification=True)

    assert production_profiles
    assert all(profile.production for profile in production_profiles)
    assert legacy_profiles
    assert all(profile.verification_only for profile in legacy_profiles)


def test_profiles_are_frozen_values() -> None:
    profile = RFC6962_MERKLE_V1
    with pytest.raises(AttributeError):
        profile.id = "changed"  # type: ignore[misc]

    assert isinstance(profile, ProtocolProfile)
