#!/usr/bin/env python3
"""Deterministic case generator for EXP-003.

Generating a preview corpus is not confirmatory execution. Confirmatory generation requires the
explicit --confirmatory flag and at least 1,000 cases, matching the preregistration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

FAMILIES = (
    "digital_authority",
    "distributed_omission",
    "ai_tool_action",
    "cyber_physical_action",
    "consequence_custody",
)

ATOMS = (
    "signature_valid",
    "producer_identified",
    "authority_current",
    "authority_event_time",
    "policy_current",
    "policy_event_time",
    "request_present",
    "execution_evidence_present",
    "result_evidence_present",
    "result_inside_window",
    "expectation_present",
    "coverage_gap_present",
    "verifier_trusted",
    "source_roots_independent",
    "shared_upstream_root",
    "contradiction_present",
    "alternative_cause_present",
    "evidence_available",
    "observation_qualifies",
    "message_fresh",
    "reference_values_fresh",
)


def holdout_value(case_id: str, seed: int) -> float:
    raw = hashlib.sha256(f"{case_id}:{seed}".encode()).digest()
    return int.from_bytes(raw, "big") / float(1 << 256)


def make_case(index: int, rng: random.Random, holdout_seed: int) -> dict[str, object]:
    case_id = f"E3-{index:06d}"
    family = FAMILIES[index % len(FAMILIES)]
    facts = {name: bool(rng.getrandbits(1)) for name in ATOMS}

    facts["request_present"] = True
    if facts["shared_upstream_root"]:
        facts["source_roots_independent"] = False
    if not facts["result_evidence_present"]:
        facts["observation_qualifies"] = False
        facts["result_inside_window"] = False
    if not facts["execution_evidence_present"]:
        facts["result_inside_window"] = False

    return {
        "case_id": case_id,
        "family": family,
        "facts": facts,
        "holdout": holdout_value(case_id, holdout_seed) < 0.2,
    }


def generate(count: int, seed: int, holdout_seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    return [make_case(i + 1, rng, holdout_seed) for i in range(count)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=39054063)
    parser.add_argument("--holdout-seed", type=int, default=177813580)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirmatory", action="store_true")
    args = parser.parse_args()

    if args.confirmatory and args.count < 1000:
        parser.error("confirmatory generation requires at least 1,000 cases")
    if not args.confirmatory and args.count >= 1000:
        parser.error("use --confirmatory for a corpus of 1,000 or more cases")

    payload = {
        "experiment": "EXP-003",
        "confirmatory": args.confirmatory,
        "count": args.count,
        "seed": args.seed,
        "holdout_seed": args.holdout_seed,
        "cases": generate(args.count, args.seed, args.holdout_seed),
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
