"""Synthetic, local-only SDK -> signed bundle -> strict CLI verification example.

No key is saved. --deterministic-smoke uses a PUBLIC test key, never deployment trust.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.core.bundle import EvidenceProofBundle
from ets.core.log import InMemoryAppendOnlyLog
from ets.core.proofs import generate_inclusion_proof
from ets.core.signing import Ed25519TreeHeadSigner
from ets.core.tree_head import SignedTreeHead
from ets.sdk import append_evidence, create_evidence, hash_evidence, verify_inclusion_proof
from ets.verifier.service import TreeHeadTrustStore, VerifierPolicy, verify_offline_bundle

SAMPLE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
LOG_ID = "ets-synthetic-sdk-example"
KEY_ID = "synthetic-example-key-not-production"
RECIPES = json.loads(Path(__file__).with_name("industry_recipes.json").read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def create_example(
    output: Path, *, deterministic_smoke: bool = False, industry: str = "manufacturing"
) -> dict[str, Any]:
    """Write only synthetic artifacts into a new directory; fail rather than overwrite."""
    recipe = RECIPES[industry]
    output.mkdir(parents=False, exist_ok=False)
    # The fixed seed is a public test identity. The normal example generates an
    # ephemeral key instead. Neither key is exported or a production identity.
    key = (
        Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"ETS PUBLIC SDK SMOKE KEY").digest())
        if deterministic_smoke
        else Ed25519PrivateKey.generate()
    )
    artifact = (
        f"SYNTHETIC {industry} artifact for {recipe['subject_ref']}; not a real record\n".encode()
    )
    (output / "synthetic-artifact.txt").write_bytes(artifact)
    event = create_evidence(
        {
            "event_id": f"evt_sdk_synthetic_{industry}_01",
            "tenant_id": "synthetic-tenant",
            "workspace_id": "sample",
            "evidence_id": f"evidence_synthetic_{industry}_01",
            "event_type": recipe["event_type"],
            "subject_ref": recipe["subject_ref"],
            "content_hash": hashlib.sha256(artifact).hexdigest(),
            "content_hash_alg": "sha256",
            "metadata": {
                "synthetic": True,
                **recipe["metadata"],
                "claim_limit": recipe["limit"],
            },
            "created_at_utc": SAMPLE_TIME,
            "source_system": "sdk-example",
            "correlation_id": "workflow-demo-01",
        }
    )
    store = InMemoryAppendOnlyLog()
    entry = append_evidence(store, event)
    assert entry.event_hash == hash_evidence(event)
    proof = generate_inclusion_proof(store.list_entries(), entry.log_index, SAMPLE_TIME)
    inclusion = verify_inclusion_proof(proof).model_copy(update={"verified_at_utc": SAMPLE_TIME})
    signer = Ed25519TreeHeadSigner(key.private_bytes_raw().hex(), KEY_ID)
    head = signer.sign(
        SignedTreeHead(
            tree_size=proof.tree_size,
            root_hash=proof.root_hash,
            created_at_utc=SAMPLE_TIME,
            log_id=LOG_ID,
        )
    )
    bundle = EvidenceProofBundle(
        event=event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=head,
        inclusion_proof=proof,
        verification_result=inclusion,
    )
    trust = TreeHeadTrustStore.model_validate(
        {
            "keys": [
                {
                    "key_id": KEY_ID,
                    "signature_alg": "ed25519",
                    "public_key_hex": key.public_key().public_bytes_raw().hex(),
                }
            ]
        }
    )
    outcome = verify_offline_bundle(
        bundle, trust_store=trust, policy=VerifierPolicy(expected_log_id=LOG_ID)
    )
    if not outcome.valid or not outcome.signature_verified:
        raise RuntimeError("Synthetic signed round trip did not verify")
    write_json(output / "event.json", event.model_dump(mode="json"))
    write_json(output / "bundle.json", bundle.model_dump(mode="json"))
    write_json(output / "sample-trust.json", trust.model_dump(mode="json"))
    tampered = copy.deepcopy(bundle.model_dump(mode="json"))
    tampered["event"]["metadata"]["tampered_after_commit"] = True
    write_json(output / "tampered-bundle.json", tampered)
    # A local SDK append returns LogEntry, NOT the remote EventCommitReceiptV1.
    summary = {
        "synthetic_only": True,
        "industry": industry,
        "public_test_key": deterministic_smoke,
        "private_key_saved": False,
        "event_id": entry.event.event_id,
        "event_hash": entry.event_hash,
        "log_index": entry.log_index,
        "expected_log_id": LOG_ID,
        "library_valid": outcome.valid,
        "standing_status": outcome.standing_status,
        "claim_limit": "Selected sample key and checkpoint only; not real-world truth",
    }
    write_json(output / "sample-summary.json", summary)
    return summary


def verify_exports(output: Path, *, verifier: Path | None = None) -> dict[str, str]:
    """Exercise exported bytes through the existing CLI, not cached author results."""
    command = [str(verifier.resolve())] if verifier else [sys.executable, "-m", "ets.verifier.cli"]
    statuses: dict[str, str] = {}
    cases = (
        ("signed", "bundle.json", True, 0, "valid"),
        ("tampered", "tampered-bundle.json", True, 1, "invalid"),
        ("missing-trust", "bundle.json", False, 2, "indeterminate"),
    )
    for name, filename, use_trust, expected_exit, expected_status in cases:
        args = [
            *command,
            "offline",
            str(output / filename),
            "--expected-log-id",
            LOG_ID,
            "--report",
            str(output / f"{name}-report.json"),
        ]
        if use_trust:
            args.extend(["--trust-store", str(output / "sample-trust.json")])
        result = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False
        )
        if result.stderr or result.returncode != expected_exit:
            raise RuntimeError(f"{name}: unexpected verifier exit {result.returncode}")
        outcome = json.loads(result.stdout)
        report = json.loads((output / f"{name}-report.json").read_text(encoding="utf-8"))
        if outcome.get("status") != expected_status or report.get("outcome") != outcome:
            raise RuntimeError(f"{name}: unexpected result/report contract")
        statuses[name] = outcome["status"]
    return statuses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory; parent must exist"
    )
    parser.add_argument(
        "--deterministic-smoke",
        action="store_true",
        help="Use PUBLIC deterministic test key; never production trust",
    )
    parser.add_argument(
        "--verifier", type=Path, help="Optional complete frozen CLI installation's executable"
    )
    parser.add_argument("--industry", choices=sorted(RECIPES), default="manufacturing")
    args = parser.parse_args()
    output = args.output.resolve()
    summary = create_example(
        output, deterministic_smoke=args.deterministic_smoke, industry=args.industry
    )
    summary["cli_statuses"] = verify_exports(output, verifier=args.verifier)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
