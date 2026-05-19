"""Command line verifier for local ETS JSON artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ets.verifier import compute_event_hash, verify_event_hash, verify_inclusion


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "event-hash":
            return _event_hash(args.path, args.expected)
        if args.command == "inclusion-proof":
            return _inclusion_proof(args.path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}, sort_keys=True))
        return 2

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ets-verify", description="Verify ETS JSON artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    event_hash = subparsers.add_parser("event-hash", help="compute or verify an event hash")
    event_hash.add_argument("path", type=Path, help="path to an EvidenceEvent JSON file")
    event_hash.add_argument("--expected", help="expected event hash to compare")

    inclusion = subparsers.add_parser("inclusion-proof", help="verify an inclusion proof")
    inclusion.add_argument("path", type=Path, help="path to an InclusionProof JSON file")

    return parser


def _event_hash(path: Path, expected: str | None) -> int:
    event = _read_json(path)
    if expected is None:
        print(json.dumps({"event_hash": compute_event_hash(event)}, sort_keys=True))
        return 0

    result = verify_event_hash(event, expected)
    print(json.dumps(result.__dict__, sort_keys=True))
    return 0 if result.valid else 1


def _inclusion_proof(path: Path) -> int:
    proof = _read_json(path)
    result = verify_inclusion(proof)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
