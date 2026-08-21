"""Command line verifier for local and live ETS artifacts."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

try:
    from ets.version import __version__
except ImportError:  # pragma: no cover - defensive console-script fallback
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("ets")
    except PackageNotFoundError:
        __version__ = "0.1.0"

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
from ets.verifier.service import (
    TreeHeadTrustStore,
    VerificationTransportError,
    VerifierPolicy,
    verify_offline_bundle,
    verify_online_event,
)

MAX_OFFLINE_BUNDLE_BYTES = 4 * 1024 * 1024
MAX_TRUST_STORE_BYTES = 1024 * 1024


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
        if args.command == "offline":
            return _offline(
                args.path,
                args.trust_store,
                args.expected_log_id,
                args.allow_unsigned,
            )
        if args.command == "online":
            return _online(
                args.base_url,
                args.event_id,
                args.trust_store,
                args.expected_log_id,
                args.allow_unsigned,
                tuple(args.allowed_host or ()),
                args.allow_http,
                args.tenant,
                args.workspace,
                args.timeout,
                args.max_response_bytes,
            )
        if args.command == "certificate":
            return _certificate(args.path, args.format, args.out)
        if args.command == "tree-head":
            return _tree_head(args.previous, args.latest)
        if args.command == "election-proof":
            return _election_proof(args.path)
    except (
        OSError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
        VerificationTransportError,
    ) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}, sort_keys=True))
        return 2

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ets-verify", description="Verify ETS artifacts")
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

    bundle = subparsers.add_parser("bundle", help="verify a legacy ETS proof bundle")
    bundle.add_argument("path", type=Path, help="path to an EvidenceProofBundle JSON file")

    offline = subparsers.add_parser(
        "offline",
        help="strictly verify a downloaded bundle against an out-of-band trust store",
    )
    offline.add_argument("path", type=Path, help="path to an EvidenceProofBundle JSON file")
    _add_runtime_policy_arguments(offline)

    online = subparsers.add_parser(
        "online",
        help="verify an event against a live ETS log and current append-only state",
    )
    online.add_argument("base_url", help="ETS service base URL; HTTPS is required by default")
    online.add_argument("event_id", help="event ID to verify")
    _add_runtime_policy_arguments(online)
    online.add_argument(
        "--allowed-host",
        action="append",
        help="allowed ETS hostname; may be repeated; recommended for automation",
    )
    online.add_argument(
        "--allow-http",
        action="store_true",
        help="allow cleartext HTTP for local development only",
    )
    online.add_argument("--tenant", help="X-ETS-Tenant value for local-header auth only")
    online.add_argument("--workspace", help="X-ETS-Workspace value for local-header auth only")
    online.add_argument("--timeout", type=float, default=5.0, help="request timeout in seconds")
    online.add_argument(
        "--max-response-bytes",
        type=int,
        default=2 * 1024 * 1024,
        help="maximum bytes accepted from any verifier endpoint",
    )

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


def _add_runtime_policy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--trust-store",
        type=Path,
        help="path to ets.verifier_trust.v1 JSON; required unless --allow-unsigned",
    )
    parser.add_argument("--expected-log-id", help="require an exact ETS log_id")
    parser.add_argument(
        "--allow-unsigned",
        action="store_true",
        help="accept unsigned checkpoints for local development only",
    )


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


def _offline(
    path: Path,
    trust_store_path: Path | None,
    expected_log_id: str | None,
    allow_unsigned: bool,
) -> int:
    payload = _read_json_limited(path, MAX_OFFLINE_BUNDLE_BYTES)
    trust_store = _load_trust_store(trust_store_path, allow_unsigned)
    result = verify_offline_bundle(
        payload,
        trust_store=trust_store,
        policy=VerifierPolicy(
            require_tree_head_signature=not allow_unsigned,
            expected_log_id=expected_log_id,
        ),
    )
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _online(
    base_url: str,
    event_id: str,
    trust_store_path: Path | None,
    expected_log_id: str | None,
    allow_unsigned: bool,
    allowed_hosts: tuple[str, ...],
    allow_http: bool,
    tenant: str | None,
    workspace: str | None,
    timeout: float,
    max_response_bytes: int,
) -> int:
    trust_store = _load_trust_store(trust_store_path, allow_unsigned)
    result = verify_online_event(
        base_url,
        event_id,
        trust_store=trust_store,
        policy=VerifierPolicy(
            require_tree_head_signature=not allow_unsigned,
            expected_log_id=expected_log_id,
        ),
        headers=_verification_headers(tenant=tenant, workspace=workspace),
        allowed_hosts=allowed_hosts,
        allow_insecure_http=allow_http,
        timeout_seconds=timeout,
        max_response_bytes=max_response_bytes,
    )
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.valid else 1


def _load_trust_store(path: Path | None, allow_unsigned: bool) -> TreeHeadTrustStore:
    if path is None:
        if allow_unsigned:
            return TreeHeadTrustStore()
        raise ValueError("--trust-store is required unless --allow-unsigned is explicitly set")
    if path.stat().st_size > MAX_TRUST_STORE_BYTES:
        raise ValueError("trust store exceeds 1 MiB")
    return TreeHeadTrustStore.model_validate_json(path.read_text(encoding="utf-8"))


def _verification_headers(*, tenant: str | None, workspace: str | None) -> dict[str, str]:
    bearer_token = os.getenv("ETS_VERIFY_BEARER_TOKEN")
    api_key = os.getenv("ETS_VERIFY_API_KEY")
    if bearer_token and api_key:
        raise ValueError("set only one of ETS_VERIFY_BEARER_TOKEN or ETS_VERIFY_API_KEY")

    headers: dict[str, str] = {"Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if api_key:
        headers["X-ETS-API-Key"] = api_key
    if tenant:
        headers["X-ETS-Tenant"] = tenant
    if workspace:
        headers["X-ETS-Workspace"] = workspace
    return headers


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


def _read_json_limited(path: Path, max_bytes: int) -> Any:
    if path.stat().st_size > max_bytes:
        raise ValueError(f"JSON input exceeds {max_bytes} bytes")
    return _read_json(path)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
