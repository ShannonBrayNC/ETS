#!/usr/bin/env python3
"""Condition C evaluator: RFC 9334-style RATS+ realization of the frozen calculus.

This implementation is intentionally independent of condition_b.py. It uses RATS role language
while emitting the same normalized proposition types for equivalence comparison.
"""

from __future__ import annotations

from collections.abc import Mapping


def evaluate(case: Mapping[str, object]) -> dict[str, object]:
    facts = case["facts"]
    if not isinstance(facts, Mapping):
        raise TypeError("case['facts'] must be a mapping")

    attestation_result: set[str] = set()
    policy_trace: dict[str, str] = {}

    def emit(kind: str, policy_rule: str) -> None:
        attestation_result.add(kind)
        policy_trace[kind] = policy_rule

    if facts.get("signature_valid"):
        emit("INTEGRITY_VALID", "RATS-PRIM-INTEGRITY")
    if facts.get("producer_identified"):
        emit("PRODUCER_IDENTIFIED", "RATS-PRIM-IDENTITY")
    if facts.get("request_present"):
        emit("REQUESTED", "RATS-APP-REQUEST")
    if facts.get("verifier_trusted"):
        emit("VERIFIER_TRUSTED", "RATS-RP-VERIFIER-TRUST")

    if all(
        facts.get(atom)
        for atom in (
            "producer_identified",
            "authority_event_time",
            "policy_event_time",
            "request_present",
        )
    ):
        emit("STANDING_VALID", "RATS+-R-AUTH-01")

    if facts.get("execution_evidence_present"):
        emit("EXECUTED", "RATS+-R-EXEC-01")

    result_supported = bool(
        facts.get("result_evidence_present") and facts.get("observation_qualifies")
    )
    if result_supported:
        emit("RESULT_OBSERVED", "RATS+-R-RESULT-01")

    if facts.get("expectation_present") and facts.get("coverage_gap_present"):
        emit("OMISSION_SUPPORTED", "RATS+-R-OMISSION-01")

    if facts.get("source_roots_independent") and not facts.get("shared_upstream_root"):
        emit("INDEPENDENT_SOURCE", "RATS+-R-INDEP-01")

    consequence_supported = all(
        (
            facts.get("execution_evidence_present"),
            result_supported,
            facts.get("result_inside_window"),
            not facts.get("contradiction_present"),
            not facts.get("alternative_cause_present"),
        )
    )
    if consequence_supported:
        emit("CONSEQUENCE_SUPPORTED", "RATS+-R-CONSEQ-01")

    return {
        "rats_roles": {
            "attester": "synthetic-source-set",
            "verifier": "condition-c-verifier",
            "relying_party": "normalized-output-consumer",
        },
        "attestation_result": sorted(attestation_result),
        "policy_trace": policy_trace,
    }


def conclusions(case: Mapping[str, object]) -> set[str]:
    return set(evaluate(case)["attestation_result"])
