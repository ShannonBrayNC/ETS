#!/usr/bin/env python3
"""Condition B evaluator: frozen non-collapse calculus for EXP-003."""

from __future__ import annotations

from collections.abc import Mapping


def evaluate(case: Mapping[str, object]) -> dict[str, object]:
    facts = case["facts"]
    if not isinstance(facts, Mapping):
        raise TypeError("case['facts'] must be a mapping")

    conclusions: set[str] = set()
    traces: dict[str, dict[str, object]] = {}

    def support(kind: str, rule_id: str, premises: list[str]) -> None:
        conclusions.add(kind)
        traces[kind] = {
            "rule_id": rule_id,
            "premise_ids": premises,
            "source_roots": [],
            "limitations": [],
        }

    if facts.get("signature_valid"):
        support("INTEGRITY_VALID", "PRIM-INTEGRITY", ["signature_valid"])
    if facts.get("producer_identified"):
        support("PRODUCER_IDENTIFIED", "PRIM-IDENTITY", ["producer_identified"])
    if facts.get("request_present"):
        support("REQUESTED", "PRIM-REQUEST", ["request_present"])
    if facts.get("verifier_trusted"):
        support("VERIFIER_TRUSTED", "PRIM-VERIFIER", ["verifier_trusted"])

    standing_atoms = [
        "producer_identified",
        "authority_event_time",
        "policy_event_time",
        "request_present",
    ]
    if all(facts.get(atom) for atom in standing_atoms):
        support("STANDING_VALID", "R-AUTH-01", standing_atoms)

    if facts.get("execution_evidence_present"):
        support("EXECUTED", "R-EXEC-01", ["execution_evidence_present"])

    result_atoms = ["result_evidence_present", "observation_qualifies"]
    if all(facts.get(atom) for atom in result_atoms):
        support("RESULT_OBSERVED", "R-RESULT-01", result_atoms)

    omission_atoms = ["expectation_present", "coverage_gap_present"]
    if all(facts.get(atom) for atom in omission_atoms):
        support("OMISSION_SUPPORTED", "R-OMISSION-01", omission_atoms)

    if facts.get("source_roots_independent") and not facts.get("shared_upstream_root"):
        support(
            "INDEPENDENT_SOURCE",
            "R-INDEP-01",
            ["source_roots_independent", "shared_upstream_root=false"],
        )

    consequence_atoms = [
        "execution_evidence_present",
        "result_evidence_present",
        "observation_qualifies",
        "result_inside_window",
    ]
    no_defeater = not facts.get("contradiction_present") and not facts.get(
        "alternative_cause_present"
    )
    if all(facts.get(atom) for atom in consequence_atoms) and no_defeater:
        support("CONSEQUENCE_SUPPORTED", "R-CONSEQ-01", consequence_atoms)

    return {"conclusions": sorted(conclusions), "support_traces": traces}


def conclusions(case: Mapping[str, object]) -> set[str]:
    return set(evaluate(case)["conclusions"])
