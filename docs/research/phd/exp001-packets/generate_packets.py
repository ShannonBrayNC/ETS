#!/usr/bin/env python3
"""Deterministically materialize the 36 frozen EXP-001 evaluator packets.

This script performs pre-execution artifact generation only. It does not recruit
participants, collect responses, score outcomes, or execute EXP-001.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "packet_source.json"
OUT = ROOT / "rendered"
MANIFEST = ROOT / "rendered_sha256.json"

QUESTIONS = [
    "What events or states are directly supported by the evidence?",
    "What conclusions are inferred rather than directly observed?",
    "Which actor/action possessed valid standing at the relevant time, if established?",
    (
        "What action was requested, what action was executed, and what consequence/result "
        "was actually observed?"
    ),
    "What material facts remain unknown, unavailable, contradictory, stale, or unverified?",
    "What is the strongest defensible overall conclusion without exceeding the evidence?",
]

FORMAT_BY_CONDITION = {"A": "M", "B": "R", "C": "K"}


def render(scenario_id: str, scenario: dict, condition: str) -> str:
    fmt = FORMAT_BY_CONDITION[condition]
    lines = [
        f"# Scenario {scenario_id[1:]} — Format {fmt}",
        "",
        "## Evidence representation",
        "",
    ]

    if condition == "A":
        lines += [
            "**Provenance-oriented representation**",
            "",
            (
                "The following entities, activities, agents, records, and temporal facts are "
                "present in the provenance bundle:"
            ),
        ]
        lines += [f"- P{i:02d}: {fact}" for i, fact in enumerate(scenario["facts"], 1)]
        lines += [
            "",
            (
                "Relationship interpretation follows ordinary provenance semantics. No "
                "additional verifier rule is supplied beyond the represented records and "
                "relationships."
            ),
        ]
    elif condition == "B":
        lines += [
            "**Domain-extended provenance representation**",
            "",
            (
                "The same factual record is represented with domain-specific relationship "
                "types and state labels:"
            ),
        ]
        lines += [
            f"- D{i:02d} [domain fact]: {fact}"
            for i, fact in enumerate(scenario["facts"], 1)
        ]
        lines += [
            "",
            (
                "Domain extensions may distinguish authorization, policy, source dependency, "
                "command, acknowledgment, sensor state, or result records where those concepts "
                "appear above. No separate bounded-verification rule is supplied."
            ),
        ]
    else:
        lines += [
            "**Bounded evidence representation**",
            "",
            (
                "The same factual record is represented as evidence claims with explicit "
                "verification boundaries:"
            ),
        ]
        lines += [
            f"- E{i:02d} [evidenced fact]: {fact}"
            for i, fact in enumerate(scenario["facts"], 1)
        ]
        lines += ["", "**Boundary annotations**"]
        lines += [f"- {item}" for item in scenario["boundary_annotations"]]
        lines += [
            "",
            "**Strongest bounded conclusion encoded by the representation**",
            f"- {scenario['strongest_bounded_conclusion']}",
        ]

    lines += ["", "## Reconstruction questions", ""]
    lines += [f"{i}. {q}" for i, q in enumerate(QUESTIONS, 1)]
    lines += [
        "",
        "---",
        (
            "Do not infer facts that are not represented. Record uncertainty explicitly when "
            "the evidence does not resolve a question."
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}

    expected = 0
    for scenario_id in sorted(source):
        for condition in ("A", "B", "C"):
            expected += 1
            fmt = FORMAT_BY_CONDITION[condition]
            filename = f"scenario-{scenario_id[1:]}-format-{fmt}.md"
            content = render(scenario_id, source[scenario_id], condition)
            path = OUT / filename
            path.write_text(content, encoding="utf-8", newline="\n")
            hashes[filename] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    if expected != 36:
        raise RuntimeError(f"Expected 36 packets, generated {expected}")

    MANIFEST.write_text(
        json.dumps(
            {
                "execution_state": "NOT EXECUTED",
                "seed": "a5c57f031335d92aa42b64affd657334",
                "format_mapping": FORMAT_BY_CONDITION,
                "packet_count": expected,
                "sha256": hashes,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
