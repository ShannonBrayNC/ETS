#!/usr/bin/env python3
"""EXP-001 preregistered descriptive analysis implementation.

This module contains no participant data and does not execute EXP-001 by itself.
It validates supplied CSV inputs and computes the descriptive metrics frozen in
EXP-001_ANALYSIS_SKELETON.md.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

ASSIGNMENT_COLUMNS = {
    "evaluator_id",
    "evaluator_stratum",
    "scenario_id",
    "condition_code",
    "presentation_order",
    "randomization_seed_ref",
}
RESPONSE_COLUMNS = {
    "evaluator_id",
    "scenario_id",
    "condition_code",
    "question_id",
    "response_text",
    "confidence_1_to_5",
    "elapsed_seconds",
}
SCORE_COLUMNS = {
    "evaluator_id",
    "scenario_id",
    "condition_code",
    "question_id",
    "claim_id",
    "claim_text",
    "primary_label",
    "error_UI",
    "error_SC",
    "error_CR",
    "error_FC",
    "error_MC",
    "error_EO",
    "error_SD",
    "error_IO",
    "error_ST",
    "error_TQ",
    "scorer_id",
    "adjudication_status",
}
LABELS = {
    "SUPPORTED",
    "UNSUPPORTED",
    "CONTRADICTED",
    "INDETERMINATE",
    "NOT_APPLICABLE",
}
ERROR_FIELDS = {
    "unsupported_inference": "error_UI",
    "standing_collapse": "error_SC",
    "command_result_collapse": "error_CR",
    "false_completeness": "error_FC",
    "missed_contradiction": "error_MC",
    "epistemic_overstatement": "error_EO",
}


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def validate(
    assignments: list[dict[str, str]],
    responses: list[dict[str, str]],
    scores: list[dict[str, str]],
) -> None:
    assignment_keys = {
        (row["evaluator_id"], row["scenario_id"], row["condition_code"])
        for row in assignments
    }
    for row in responses:
        key = (row["evaluator_id"], row["scenario_id"], row["condition_code"])
        if key not in assignment_keys:
            raise ValueError(f"response not present in assignment table: {key}")
        confidence = int(row["confidence_1_to_5"])
        if confidence not in range(1, 6):
            raise ValueError(f"confidence outside 1-5: {key}")
        if float(row["elapsed_seconds"]) < 0:
            raise ValueError(f"negative elapsed time: {key}")
    for row in scores:
        if row["primary_label"] not in LABELS:
            raise ValueError(f"invalid primary label: {row['primary_label']}")


def summarize_condition(
    condition: str,
    assignments: list[dict[str, str]],
    responses: list[dict[str, str]],
    scores: list[dict[str, str]],
) -> dict[str, Any]:
    assigned = [row for row in assignments if row["condition_code"] == condition]
    answered = [row for row in responses if row["condition_code"] == condition]
    scored = [row for row in scores if row["condition_code"] == condition]
    labels = Counter(row["primary_label"] for row in scored)
    assertion_count = sum(
        labels[label] for label in LABELS - {"NOT_APPLICABLE"}
    )
    supported = labels["SUPPORTED"]
    errors: dict[str, dict[str, float | int | None]] = {}
    for name, field in ERROR_FIELDS.items():
        denominator = sum(
            1 for row in scored if row["primary_label"] != "NOT_APPLICABLE"
        )
        numerator = sum(1 for row in scored if truthy(row[field]))
        errors[name] = {
            "numerator": numerator,
            "denominator": denominator,
            "rate": numerator / denominator if denominator else None,
        }
    elapsed = [float(row["elapsed_seconds"]) for row in answered]
    confidence = Counter(int(row["confidence_1_to_5"]) for row in answered)
    precision_denominator = (
        supported + labels["UNSUPPORTED"] + labels["CONTRADICTED"]
    )
    return {
        "condition": condition,
        "evaluator_count": len({row["evaluator_id"] for row in assigned}),
        "scenario_exposures": len(assigned),
        "substantive_assertion_count": assertion_count,
        "labels": {label: labels[label] for label in sorted(LABELS)},
        "error_metrics": errors,
        "supported_claim_precision": {
            "numerator": supported,
            "denominator": precision_denominator,
            "rate": (
                supported / precision_denominator
                if precision_denominator
                else None
            ),
        },
        "reconstruction_time_seconds": {
            "mean": mean(elapsed) if elapsed else None,
            "median": median(elapsed) if elapsed else None,
        },
        "confidence_distribution": {
            str(score): confidence[score] for score in range(1, 6)
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assignments = read_csv(args.assignments, ASSIGNMENT_COLUMNS)
    responses = read_csv(args.responses, RESPONSE_COLUMNS)
    scores = read_csv(args.scores, SCORE_COLUMNS)
    validate(assignments, responses, scores)

    conditions = sorted({row["condition_code"] for row in assignments})
    summaries = [
        summarize_condition(condition, assignments, responses, scores)
        for condition in conditions
    ]
    output = {
        "experiment": "EXP-001",
        "analysis_scope": "preregistered descriptive metrics",
        "conditions": summaries,
    }
    rendered = json.dumps(output, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
