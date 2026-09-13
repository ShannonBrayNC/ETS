from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ets.core.canonical_json import canonical_sha256
from ets.qualification.hardware import (
    HardwareQualificationReport,
    HardwareQualificationRun,
    build_qualification_report,
)

_FIXTURE_ROOT = Path(__file__).parents[2] / "docs" / "qualification" / "fixtures" / "hqp1"
_VALID_RUN = _FIXTURE_ROOT / "valid" / "edge-qualified-run.json"
_VALID_REPORT = _FIXTURE_ROOT / "valid" / "edge-qualified-report.json"
_NEGATIVE_MUTATIONS = _FIXTURE_ROOT / "invalid" / "mutations.json"


def test_valid_fixture_round_trips_to_deterministic_report() -> None:
    run = HardwareQualificationRun.model_validate_json(_VALID_RUN.read_text(encoding="utf-8"))
    expected_report = HardwareQualificationReport.model_validate_json(
        _VALID_REPORT.read_text(encoding="utf-8")
    )

    actual_report = build_qualification_report(run)

    assert actual_report == expected_report
    assert actual_report.report_digest_sha256 == (
        "a00545eb5b90798321977170c87f3eef19df2c999cd03779c03f1dae5d118da3"
    )


def test_negative_mutation_vectors_are_rejected() -> None:
    source = json.loads(_VALID_RUN.read_text(encoding="utf-8"))
    fixture = json.loads(_NEGATIVE_MUTATIONS.read_text(encoding="utf-8"))

    for case in fixture["cases"]:
        candidate = json.loads(json.dumps(source))
        _replace_json_pointer(candidate, case["json_pointer"], case["value"])
        if case["recompute_run_digest"]:
            candidate.pop("run_digest_sha256", None)
            candidate["run_digest_sha256"] = canonical_sha256(candidate)

        with pytest.raises(ValidationError, match=case["expected_failure"]):
            HardwareQualificationRun.model_validate_json(json.dumps(candidate))


def _replace_json_pointer(document: Any, pointer: str, value: Any) -> None:
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer.split("/")[1:]]
    target = document
    for token in tokens[:-1]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    last = tokens[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
