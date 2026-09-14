from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).parents[2]
_CORPUS = _ROOT / "docs" / "qualification" / "corpora" / "ets-edge-hqp-corpus-v1.json"
_RUNBOOK = (
    _ROOT
    / "docs"
    / "qualification"
    / "physical"
    / "EDGE_RT0_PHYSICAL_EXECUTION_RUNBOOK_V1.md"
)
_TEMPLATE = (
    _ROOT
    / "docs"
    / "qualification"
    / "physical"
    / "edge-rt0-dut-readiness.template.json"
)


def test_physical_runbook_covers_exact_edge_corpus_case_inventory() -> None:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    runbook = _RUNBOOK.read_text(encoding="utf-8")

    expected = set(corpus["case_order"])
    observed = set(re.findall(r"EDGE-HQP-[A-Z]{3}-001", runbook))

    assert observed == expected
    assert len(expected) == 17


def test_readiness_template_matches_edge_profile_and_starts_non_authorized() -> None:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    readiness = json.loads(_TEMPLATE.read_text(encoding="utf-8"))

    assert readiness["profile"]["profile_id"] == corpus["profile_id"]
    assert readiness["profile"]["profile_version"] == corpus["profile_version"]
    assert readiness["profile"]["corpus_id"] == corpus["corpus_id"]
    assert readiness["profile"]["corpus_version"] == corpus["corpus_version"]
    assert readiness["profile"]["target_class_id"] == (
        corpus["reference_target_class"]["target_class_id"]
    )

    assert readiness["execution_state"] == "template_not_executed"
    assert readiness["qualification_claim"] is False
    assert readiness["preflight"]["preflight_authorized"] is False
    assert readiness["hardware_envelope"]["meets_edge_mvp_minimum"] is False
    assert all(value is False for value in readiness["lab_controls"].values())
    assert all(value is False for value in readiness["fault_boundaries"].values())


def test_readiness_template_contains_all_claim_critical_corpus_dimensions() -> None:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    readiness = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    target = corpus["reference_target_class"]

    firmware = readiness["dut"]["firmware"]
    environment = readiness["qualification_environment"]

    assert set(target["required_device_firmware_fields"]) <= set(firmware)
    assert set(target["required_environment_dimensions"]) <= set(environment)


def test_physical_template_preserves_secret_and_claim_boundaries() -> None:
    readiness = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    non_claims = " ".join(readiness["non_claims"]).lower()

    assert readiness["retention"]["secrets_private_keys_prohibited"] is True
    assert "not evidence" in non_claims
    assert "not a qualified manufacturer or model" in non_claims
    assert "semantic truth" in non_claims
    assert "production readiness" in non_claims
