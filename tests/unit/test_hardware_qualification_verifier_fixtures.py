from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ets.qualification.verifier import VerificationCheckStatus, VerificationOutcome, verify_hardware_qualification_package

_ROOT = Path(__file__).parents[2]
_FIXTURE_ROOT = _ROOT / "docs" / "qualification" / "fixtures" / "hqp2"
_VALID = _FIXTURE_ROOT / "valid"
_MUTATIONS = _FIXTURE_ROOT / "invalid" / "mutations.json"
_VERIFIER_BUILD = hashlib.sha256(b"hqp2-retained-fixture-verifier").hexdigest()


def _artifact_payloads() -> dict[str, bytes]:
    mapping = json.loads((_VALID / "artifact-map.json").read_text(encoding="utf-8"))
    return {
        artifact_id: (_VALID / relative_path).read_bytes()
        for artifact_id, relative_path in mapping.items()
    }


def _verify(
    *,
    profile_bytes: bytes | None = None,
    artifacts: dict[str, bytes] | None = None,
    independent: bool = True,
):
    return verify_hardware_qualification_package(
        profile_bytes=profile_bytes or (_VALID / "profile.json").read_bytes(),
        run_bytes=(_VALID / "run.json").read_bytes(),
        report_bytes=(_VALID / "report.json").read_bytes(),
        artifact_payloads=artifacts or _artifact_payloads(),
        verifier_id="hqp2-retained-fixture-verifier",
        verifier_build_digest_sha256=_VERIFIER_BUILD,
        independent_execution_context=independent,
        challenge_nonce="retained-fixture-challenge",
    )


def test_retained_fixture_verifies_in_clean_room() -> None:
    result = _verify()

    assert result.outcome is VerificationOutcome.VALID
    assert result.eligible_for_claimed_disposition is True
    assert result.run_digest_sha256 == "c0782f8eda93f87b346cff2c57d7bf418f14ff47d7f40f9d412257cfd486f060"
    assert result.report_digest_sha256 == "873e919b669c95565768c20662ae49bac0df1778f972fc91eef91e90a2f561c5"


def test_retained_negative_mutation_vectors_fail_expected_gate() -> None:
    vectors = json.loads(_MUTATIONS.read_text(encoding="utf-8"))["mutations"]

    for vector in vectors:
        artifacts = _artifact_payloads()
        profile_bytes = (_VALID / "profile.json").read_bytes()
        independent = True
        operation = vector["operation"]

        if operation == "append_utf8":
            target = vector["target"]
            artifacts[target] += vector["value"].encode("utf-8")
        elif operation == "replace_profile_purpose":
            profile = json.loads(profile_bytes)
            profile["purpose"] = vector["value"]
            profile_bytes = json.dumps(
                profile,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        elif operation == "set_independent_execution_context":
            independent = bool(vector["value"])
        else:
            raise AssertionError(f"unsupported retained mutation: {operation}")

        result = _verify(
            profile_bytes=profile_bytes,
            artifacts=artifacts,
            independent=independent,
        )

        assert result.outcome.value == vector["expected_outcome"]
        check = next(item for item in result.checks if item.check_id == vector["expected_check"])
        assert check.status is VerificationCheckStatus.FAIL
