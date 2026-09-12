#!/usr/bin/env python3
"""Condition A evaluator: strongest frozen rich-profile baseline for EXP-003."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "BASELINE_PROFILE.json"


def _profile() -> Mapping[str, object]:
    return json.loads(PROFILE_PATH.read_text())


def conclusions(case: Mapping[str, object]) -> set[str]:
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

    for rule in _profile()["application_rules"]:
        if not isinstance(rule, Mapping):
            raise TypeError("application rule must be a mapping")
        required = rule.get("requires_atoms", [])
        forbidden = rule.get("forbids_atoms", [])
        if all(facts.get(atom) for atom in required) and not any(
            facts.get(atom) for atom in forbidden
        ):
            out.add(str(rule["conclusion"]))
    return out
