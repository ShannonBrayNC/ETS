"""Deterministic election RC demo artifact generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ets.election.demo import build_sample_ledger
from ets.election.ledger import export_election_audit_log, verify_election_chain
from ets.election.proofs import (
    create_election_inclusion_proof,
    create_election_root_manifest,
    export_election_proof_report,
    verify_election_inclusion_bundle,
)

DEMO_GENERATED_AT = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class ElectionDemoArtifacts:
    """Paths written by the RC election demo."""

    output_dir: Path
    manifest_path: Path
    audit_log_path: Path
    proof_path: Path
    verification_path: Path
    tamper_path: Path
    walkthrough_path: Path


def build_election_demo_payload() -> dict[str, Any]:
    """Build deterministic, public-safe election RC demo payloads."""

    ledger = build_sample_ledger()
    entries = ledger.list_entries()
    manifest = create_election_root_manifest(
        entries,
        milestone="pre_election",
        generated_at_utc=DEMO_GENERATED_AT,
    )
    proof = create_election_inclusion_proof(
        entries,
        "elx_evt_0002",
        milestone="pre_election",
        generated_at_utc=DEMO_GENERATED_AT,
    )
    verification = verify_election_inclusion_bundle(proof)
    chain = verify_election_chain(entries)
    tampered = proof.model_copy(update={"leaf_hash": "0" * 64}, deep=True)
    tamper_verification = verify_election_inclusion_bundle(tampered)

    return {
        "storyboard": [
            "Import fictional election setup package",
            "Register logic and accuracy evidence",
            "Register ballot batch custody transfers",
            "Generate milestone Merkle root",
            "Publish public proof",
            "Verify valid evidence packet",
            "Demonstrate tampered artifact rejection",
            "Export audit package",
        ],
        "root_manifest": manifest.model_dump(mode="json"),
        "audit_log": export_election_audit_log(entries),
        "proof_bundle": proof.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
        "proof_report": export_election_proof_report(proof),
        "chain_integrity": {
            "valid": chain.valid,
            "entry_count": chain.entry_count,
            "tip_hash": chain.tip_hash,
            "issues": [issue.__dict__ for issue in chain.issues],
        },
        "tamper_demo": {
            "valid": tamper_verification.valid,
            "reason": tamper_verification.reason,
            "tampered_leaf_hash": tampered.leaf_hash,
            "expected_leaf_hash": proof.leaf_hash,
        },
        "privacy_boundary": {
            "stores_raw_ballots": False,
            "stores_voter_records": False,
            "public_artifacts": ["root_manifest", "proof_bundle", "audit_log"],
        },
    }


def write_election_demo_artifacts(
    output_dir: Path = Path("artifacts/election-rc-demo"),
) -> ElectionDemoArtifacts:
    """Write JSON and Markdown artifacts for the election RC demo."""

    payload = build_election_demo_payload()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "root-manifest.json"
    audit_log_path = output_dir / "audit-log.json"
    proof_path = output_dir / "proof-bundle.json"
    verification_path = output_dir / "verification-result.json"
    tamper_path = output_dir / "tamper-result.json"
    walkthrough_path = output_dir / "walkthrough.md"

    _write_json(manifest_path, payload["root_manifest"])
    _write_json(audit_log_path, payload["audit_log"])
    _write_json(proof_path, payload["proof_bundle"])
    _write_json(verification_path, payload["verification"])
    _write_json(tamper_path, payload["tamper_demo"])
    walkthrough_path.write_text(_walkthrough_markdown(payload), encoding="utf-8")

    return ElectionDemoArtifacts(
        output_dir=output_dir,
        manifest_path=manifest_path,
        audit_log_path=audit_log_path,
        proof_path=proof_path,
        verification_path=verification_path,
        tamper_path=tamper_path,
        walkthrough_path=walkthrough_path,
    )


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _walkthrough_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ETS Election RC Demo Walkthrough",
        "",
        "This walkthrough uses fictional election-adjacent evidence metadata.",
        "ETS is an evidence/audit layer, not voting or tabulation software.",
        "",
        "## Storyboard",
        "",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(payload["storyboard"], start=1))
    lines.extend(
        [
            "",
            "## Milestone Root",
            "",
            f"- Tree size: {payload['root_manifest']['tree_size']}",
            f"- Merkle root: `{payload['root_manifest']['merkle_root']}`",
            "",
            "## Verification",
            "",
            f"- Valid proof: {payload['verification']['valid']}",
            f"- Reason: {payload['verification']['reason']}",
            "",
            "## Tamper Demonstration",
            "",
            f"- Tampered proof valid: {payload['tamper_demo']['valid']}",
            f"- Failure reason: {payload['tamper_demo']['reason']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    artifacts = write_election_demo_artifacts()
    print(
        json.dumps(
            {
                "output_dir": artifacts.output_dir.as_posix(),
                "manifest": artifacts.manifest_path.as_posix(),
                "audit_log": artifacts.audit_log_path.as_posix(),
                "proof": artifacts.proof_path.as_posix(),
                "verification": artifacts.verification_path.as_posix(),
                "tamper": artifacts.tamper_path.as_posix(),
                "walkthrough": artifacts.walkthrough_path.as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
