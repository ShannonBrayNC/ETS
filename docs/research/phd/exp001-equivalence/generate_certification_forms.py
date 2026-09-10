#!/usr/bin/env python3
"""Generate blank EXP-001 independent fact-equivalence certification forms."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "forms"

CHECKS = [
    "Every reconstruction-material fact appears in all three conditions.",
    "No condition adds a reconstruction-material fact absent from the fact inventory.",
    "No condition silently resolves an unknown, unavailable, indeterminate, or contradictory fact.",
    "No condition upgrades a local or claimed timestamp into independently trusted time.",
    "No condition converts identity into authority or authority into current standing.",
    "No condition converts a requested command or acknowledgment into execution.",
    "No condition converts execution into consequence or result observation without evidence.",
    "Source dependence is factually preserved.",
    "Contradictions are preserved.",
    "Evidence absence is not converted into event absence without coverage evidence.",
    "Wording differences do not add causal or truth claims.",
    "Evaluator-facing formatting does not materially privilege one condition.",
]


def render_form(scenario_number: int) -> str:
    scenario = f"S{scenario_number:02d}"
    lines = [
        f"# EXP-001 Fact-Equivalence Certification — {scenario}",
        "",
        "**Execution state:** NOT EXECUTED  ",
        "**Certification state:** UNREVIEWED",
        "",
        "## Artifact references",
        "",
        f"- Scenario: `{scenario}`",
        f"- Format M packet: `../exp001-packets/rendered/scenario-{scenario_number:02d}-format-M.md`",
        f"- Format R packet: `../exp001-packets/rendered/scenario-{scenario_number:02d}-format-R.md`",
        f"- Format K packet: `../exp001-packets/rendered/scenario-{scenario_number:02d}-format-K.md`",
        "- Frozen fact inventory: `../EXP-001_FACT_EQUIVALENCE_AND_SCORING_KEY.md`",
        "- Authoritative packet hashes: `../exp001-packets/rendered_sha256.authoritative.json`",
        "",
        "## Reviewer record",
        "",
        "- Reviewer identity/code:",
        "- Reviewer independence basis:",
        "- Review date:",
        "- Result: UNSET",
        "- Signature/attestation method:",
        "",
        "## Mandatory checks",
        "",
    ]
    for index, check in enumerate(CHECKS, start=1):
        lines.append(f"{index}. [ ] PASS  [ ] FAIL — {check}")
        lines.append("   Notes:")
    lines.extend(
        [
            "",
            "## Review notes",
            "",
            "- Material non-factual differences:",
            "- Unresolved concerns:",
            "- Corrective action required:",
            "",
            "## Gate rule",
            "",
            "A FAIL blocks this scenario from confirmatory use. Author-only review must be labeled "
            "`AUTHOR-ONLY / NOT CONFIRMATORY READY` and cannot alone satisfy this gate.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for scenario_number in range(1, 13):
        path = OUT / f"S{scenario_number:02d}.md"
        path.write_text(render_form(scenario_number), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
