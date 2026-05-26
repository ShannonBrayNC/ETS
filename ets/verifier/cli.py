"""Command line verifier for local ETS JSON artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ets import __version__
from ets.core import EvidenceProofBundle
from ets.election import ElectionInclusionProofBundle, verify_election_inclusion_bundle
from ets.reports import CertificateFormat, create_certificate
from ets.verifier import (
    compare_tree_heads,
    compute_event_hash,
    verify_bundle,
    verify_consistency,
    verify_event_hash,
    verify_inclusion,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "event-hash":
            return _event_hash(args.path, args.expected)
        if args.command == "inclusion-proof":
            return _inclusion_proof(args.path)
        if args.command == "verify-proof":
            return _inclusion_proof(args.path)
        if args.command == "consistency-proof":
            return _consistency_proof(args.path)
        if args.command == "bundle":
            return _bundle(args.path)
        if args.command == "certificate":
            return _certificate(args.path, args.format, args.out)
        if args.command == "tree-head":
            return _tree_head(args.previous, args.latest)
        if args.command == "election-proof":
            return _election_proof(args.path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}, sort_keys=True))
        return 2

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ets-verify", description="Verify ETS JSON artifacts")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    event_hash = subparsers.add_parser("event-hash", help="compute or verify an event hash")
    event_hash.add_argument("path", type=Path, help="path to an EvidenceEvent JSON file")
    event_hash.add_argument("--expected", help="expected event hash to compare")

    inclusion = subparsers.add_parser("inclusion-proof", help="verify an inclusion proof")
    inclusion.add_argument("path", type=Path, help="path to an InclusionProof JSON file")

    verify_proof = subparsers.add_parser(
        "verify-proof",
        help="verify an inclusion proof using the Sprint 3 command name",
    )
    verify_proof.add_argument("path", type=Path, help="path to an InclusionProof JSON file")

    consistency = subparsers.add_parser("consistency-proof", help="verify a consistency proof")
    consistency.add_argument("path", type=Path, help="path to a ConsistencyProof JSON file")

    bundle = subparsers.add_parser("bundle", help="verify an ETS proof bundle")
    bundle.add_argument("path", type=Path, help="path to an EvidenceProofBundle JSON file")

    certificate = subparsers.add_parser("certificate", help="generate a verification certificate")
    certificate.add_argument("path", type=Path, help="path to an EvidenceProofBundle JSON file")
    certificate.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="certificate output format",
    )
    certificate.add_argument("--out", type=Path, help="write certificate to a file")

    tree_head = subparsers.add_parser("tree-head", help="compare two signed tree heads")
    tree_head.add_argument("previous", type=Path, help="path to the previously trusted tree head")
    tree_head.add_argument("latest", type=Path, help="path to the latest tree head")

    election_proof = subparsers.add_parser(
        "election-proof",
        help="verify an election inclusion proof bundle",
    )
    election_proof.add_argument(
        "path",
        type=Path,
        help="path to an ElectionInclusionProofBundle JSON file",
    )

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


def _consistency_proof(path: Path) -> int:
    proof = _read_json(path)
    result = verify_consistency(proof)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _bundle(path: Path) -> int:
    bundle = _read_json(path)
    result = verify_bundle(bundle)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _certificate(path: Path, output_format: CertificateFormat, out: Path | None) -> int:
    payload = _read_json(path)
    bundle = EvidenceProofBundle.model_validate_json(json.dumps(payload))
    content = create_certificate(bundle, output_format)
    if out is None:
        print(content)
    else:
        out.write_text(content, encoding="utf-8")
    return 0


def _tree_head(previous_path: Path, latest_path: Path) -> int:
    previous = _read_json(previous_path)
    latest = _read_json(latest_path)
    result = compare_tree_heads(previous, latest)
    print(json.dumps(result.__dict__, sort_keys=True))
    return 0 if result.valid else 1


def _election_proof(path: Path) -> int:
    payload = _read_json(path)
    bundle = ElectionInclusionProofBundle.model_validate_json(json.dumps(payload))
    result = verify_election_inclusion_bundle(bundle)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
