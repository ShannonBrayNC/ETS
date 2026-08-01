from __future__ import annotations

import pytest

from ets.core import api
from ets.core.errors import UnknownProfileError, VerificationOnlyProfileError
from ets.core.profiles import EVENT_ALPHA_UNPREFIXED_V1, EVENT_RFC6962_V1, resolve_profile
from ets.core.results import (
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
)


def test_active_profile_allows_generation() -> None:
    assert resolve_profile(EVENT_RFC6962_V1.profile_id, for_generation=True) == EVENT_RFC6962_V1


def test_legacy_profile_is_verification_only() -> None:
    assert resolve_profile(EVENT_ALPHA_UNPREFIXED_V1.profile_id) == EVENT_ALPHA_UNPREFIXED_V1
    with pytest.raises(VerificationOnlyProfileError):
        resolve_profile(EVENT_ALPHA_UNPREFIXED_V1.profile_id, for_generation=True)


def test_unknown_profile_fails_without_guessing() -> None:
    with pytest.raises(UnknownProfileError):
        resolve_profile("ets.protocol.unknown.v1")


def test_verification_result_is_immutable_and_deterministic() -> None:
    result = VerificationResult(
        status=VerificationStatus.INVALID,
        reason=VerificationReason.DIGEST_MISMATCH,
        component=VerifiedComponent.DIGEST,
        profile_id=EVENT_RFC6962_V1.profile_id,
        protocol_version="1",
        summary="Digest mismatch.",
        details={"z": 2, "a": 1},
    )
    assert result.valid is False
    assert result.to_dict()["details"] == {"a": 1, "z": 2}
    with pytest.raises(TypeError):
        result.details["new"] = True  # type: ignore[index]


def test_supported_api_manifest_is_explicit() -> None:
    assert api.__all__ == sorted(api.__all__)
    assert "SQLiteEventStore" not in api.__all__
    assert "InMemoryAppendOnlyLog" not in api.__all__
    assert "canonicalize" in api.__all__
    assert "resolve_profile" in api.__all__
    assert "VerificationResult" in api.__all__
