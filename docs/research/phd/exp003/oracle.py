#!/usr/bin/env python3
"""Independent support oracle for EXP-003.

The oracle consumes only frozen atomic facts. It does not import the condition evaluators or
NON_COLLAPSE_RULES.json. This separation prevents a condition implementation from defining its
own answer key.
"""

from __future__ import annotations

from collections.abc import Mapping


SUPPORTED_TYPES = {
    "INTEGRITY_VALID",
    "PRODUCER_IDENTIFIED",
    "REQUESTED",
    "STANDING_VALID",
    "EXECUTED",
    "RESULT_OBSERVED",
    "OMISSION_SUPPORTED",
    "INDEPENDENT_SOURCE",
    "VERIFIER_TRUSTED",
    "CONSEQUENCE_SUPPORTED",
}


def supported_conclusions(case: Mapping[str, object]) -> set[str]:
    """Return proposition types supportable from the case's atomic facts."""
    facts = case["facts"]
    if not isinstance(facts, Mapping):
        raise TypeError("case['facts'] must be a mapping")

    out: set[str] = set()
    if facts.get("signature_valid"):
        out.add("INTEGRITY_VALID")
    if facts.get("producer_identified"):
        out.add("PRODUCER_IDENTIFIED")
    if facts.get("request_present"):
        out.add("REQUESTED")
    if facts.get("verifier_trusted"):
        out.add("VERIFIER_TRUSTED")

    standing = all(
        facts.get(name)
        for name in (
            "producer_identified",
            "authority_event_time",
            "policy_event_time",
            "request_present",
        )
    )
    if standing:
        out.add("STANDING_VALID")

    if facts.get("execution_evidence_present"):
        out.add("EXECUTED")

    result_supported = bool(
        facts.get("result_evidence_present") and facts.get("observation_qualifies")
    )
    if result_supported:
        out.add("RESULT_OBSERVED")

    if facts.get("expectation_present") and facts.get("coverage_gap_present"):
        out.add("OMISSION_SUPPORTED")

    if facts.get("source_roots_independent") and not facts.get("shared_upstream_root"):
        out.add("INDEPENDENT_SOURCE")

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
        out.add("CONSEQUENCE_SUPPORTED")

    unknown = out.difference(SUPPORTED_TYPES)
    if unknown:
        raise AssertionError(f"oracle emitted unknown proposition types: {sorted(unknown)}")
    return out
