#!/usr/bin/env python3
"""Pre-result analysis skeleton for EXP-003.

This file contains metric definitions only. No confirmatory corpus or results are committed here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import condition_a
import condition_b
import condition_c_rats_plus
import oracle


def rates(cases: list[dict[str, object]], evaluator) -> dict[str, float | int]:
    promoted = 0
    unsupported = 0
    supported_available = 0
    supported_emitted = 0

    for case in cases:
        expected = oracle.supported_conclusions(case)
        actual = evaluator(case)
        promoted += len(actual)
        unsupported += len(actual.difference(expected))
        supported_available += len(expected)
        supported_emitted += len(actual.intersection(expected))

    promotion_rate = unsupported / promoted if promoted else 0.0
    recall = supported_emitted / supported_available if supported_available else 1.0
    return {
        "case_count": len(cases),
        "promoted": promoted,
        "unsupported": unsupported,
        "unsupported_semantic_promotion_rate": promotion_rate,
        "supported_available": supported_available,
        "supported_emitted": supported_emitted,
        "supported_conclusion_recall": recall,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--allow-confirmatory", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.corpus.read_text())
    if payload.get("confirmatory") and not args.allow_confirmatory:
        parser.error("confirmatory corpus analysis requires --allow-confirmatory")

    cases = payload["cases"]
    results = {
        "condition_a": rates(cases, condition_a.conclusions),
        "condition_b": rates(cases, condition_b.conclusions),
        "condition_c": rates(cases, condition_c_rats_plus.conclusions),
    }
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
