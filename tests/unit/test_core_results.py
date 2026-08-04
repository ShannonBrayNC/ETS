"""Contract tests for deterministic ETS Core verification results."""

from dataclasses import FrozenInstanceError

import pytest

from ets.core.results import (
    VerificationReason,
    VerificationResult,
    VerificationStatus,
    VerifiedComponent,
)


def test_valid_result_reports_success() -> None:
    result = VerificationResult(
        status=VerificationStatus.VALID,
        reason=VerificationReason.OK,
        component=VerifiedComponent.DIGEST,
        profile_id="ets.hash.sha256.v1",
        protocol_version="1",
        summary="Digest verified.",
        details={"z": 2, "a": 1},
    )

    assert result.valid is True
    assert result.to_dict() == {
        "status": "valid",
        "reason": "ok",
        "component": "digest",
        "profile_id": "ets.hash.sha256.v1",
        "protocol_version": "1",
        "summary": "Digest verified.",
        "details": {"a": 1, "z": 2},
    }


def test_non_valid_statuses_report_false() -> None:
    for status in VerificationStatus:
        result = VerificationResult(
            status=status,
            reason=(
                VerificationReason.OK
                if status is VerificationStatus.VALID
                else VerificationReason.PROOF_INVALID
            ),
            component=VerifiedComponent.INCLUSION_PROOF,
        )
        assert result.valid is (status is VerificationStatus.VALID)


def test_result_and_details_are_immutable() -> None:
    original_details = {"expected": "abc"}
    result = VerificationResult(
        status=VerificationStatus.INVALID,
        reason=VerificationReason.DIGEST_MISMATCH,
        component=VerifiedComponent.DIGEST,
        details=original_details,
    )

    original_details["expected"] = "changed"
    assert result.details["expected"] == "abc"

    with pytest.raises(TypeError):
        result.details["actual"] = "def"  # type: ignore[index]

    with pytest.raises(FrozenInstanceError):
        result.summary = "changed"  # type: ignore[misc]


def test_enums_have_unique_stable_values() -> None:
    for enum_type in (VerificationStatus, VerificationReason, VerifiedComponent):
        values = [member.value for member in enum_type]
        assert len(values) == len(set(values))


def test_to_dict_does_not_mutate_details() -> None:
    result = VerificationResult(
        status=VerificationStatus.UNKNOWN,
        reason=VerificationReason.PROFILE_REQUIRED,
        component=VerifiedComponent.BUNDLE,
        details={"b": 2, "a": 1},
    )

    first = result.to_dict()
    second = result.to_dict()

    assert first == second
    assert list(first["details"]) == ["a", "b"]  # type: ignore[arg-type]


def test_public_exports_are_exact() -> None:
    from ets.core import results

    assert set(results.__all__) == {
        "VerificationReason",
        "VerificationResult",
        "VerificationStatus",
        "VerifiedComponent",
    }
