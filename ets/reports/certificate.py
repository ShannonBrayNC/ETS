"""Human-readable verification certificate generation."""

from __future__ import annotations

import html
import json
from typing import Literal

from ets.core import EvidenceProofBundle
from ets.version import __version__

CertificateFormat = Literal["json", "markdown", "html"]


def create_certificate(
    bundle: EvidenceProofBundle,
    output_format: CertificateFormat = "json",
) -> str:
    """Create a verification certificate without exposing raw evidence bytes."""

    summary = _certificate_summary(bundle)
    if output_format == "json":
        return json.dumps(summary, indent=2, sort_keys=True)
    if output_format == "markdown":
        return _markdown_certificate(summary)
    if output_format == "html":
        return _html_certificate(summary)
    raise ValueError(f"unsupported certificate format: {output_format}")


def _certificate_summary(bundle: EvidenceProofBundle) -> dict[str, object]:
    return {
        "schema_version": "ets.certificate.v1",
        "event_id": bundle.event.event_id,
        "tenant_id": bundle.event.tenant_id,
        "workspace_id": bundle.event.workspace_id,
        "evidence_id": bundle.event.evidence_id,
        "event_type": bundle.event.event_type,
        "created_at_utc": bundle.event.created_at_utc.isoformat(),
        "event_hash": bundle.event_hash,
        "leaf_hash": bundle.leaf_hash,
        "hash_algorithm": "sha256",
        "log_tree_size": bundle.tree_head.tree_size,
        "log_root_hash": bundle.tree_head.root_hash,
        "log_id": bundle.tree_head.log_id,
        "proof_valid": bundle.verification_result.valid,
        "proof_reason": bundle.verification_result.reason,
        "signature_algorithm": bundle.tree_head.signature_alg,
        "signature_key_id": bundle.tree_head.public_key_id,
        "signature_present": bundle.tree_head.signature is not None,
        "verifier_version": __version__,
        "what_this_verifies": [
            "The event metadata hash matches the event payload in this certificate bundle.",
            "The event leaf is included in the referenced Merkle tree head "
            "when proof_valid is true.",
            "The certificate summarizes ETS metadata and hashes without exposing "
            "raw evidence bytes.",
        ],
        "what_this_does_not_verify": [
            "It does not verify authenticity, legality, completeness, or real-world "
            "truth of the underlying evidence.",
            "It does not verify election correctness, ballot validity, tabulation "
            "accuracy, or official results.",
            "It does not replace human, legal, compliance, or domain expert review.",
        ],
        "warnings": _warnings(bundle),
    }


def _warnings(bundle: EvidenceProofBundle) -> list[str]:
    warnings: list[str] = []
    if bundle.tree_head.signature is None:
        warnings.append("Tree head is unsigned local-mode metadata, not production trust.")
    if not bundle.verification_result.valid:
        warnings.append("Inclusion proof verification failed.")
    return warnings


def _markdown_certificate(summary: dict[str, object]) -> str:
    verifies = summary["what_this_verifies"]
    non_verifies = summary["what_this_does_not_verify"]
    verify_items = verifies if isinstance(verifies, list) else []
    non_verify_items = non_verifies if isinstance(non_verifies, list) else []
    lines = [
        "# ETS Verification Certificate",
        "",
        f"- Event ID: `{summary['event_id']}`",
        f"- Evidence ID: `{summary['evidence_id']}`",
        f"- Event hash: `{summary['event_hash']}`",
        f"- Leaf hash: `{summary['leaf_hash']}`",
        f"- Log root: `{summary['log_root_hash']}`",
        f"- Tree size: `{summary['log_tree_size']}`",
        f"- Proof status: `{summary['proof_reason']}`",
        f"- Signature present: `{summary['signature_present']}`",
        "",
        "## What This Verifies",
        *[f"- {item}" for item in verify_items if isinstance(item, str)],
        "",
        "## What This Does Not Verify",
        *[f"- {item}" for item in non_verify_items if isinstance(item, str)],
    ]
    warnings = summary["warnings"]
    if isinstance(warnings, list) and warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def _html_certificate(summary: dict[str, object]) -> str:
    rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in summary.items()
        if key not in {"warnings", "what_this_verifies", "what_this_does_not_verify"}
    )
    warnings = summary["warnings"]
    warning_items = ""
    if isinstance(warnings, list):
        warning_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings)
    verifies = summary["what_this_verifies"]
    non_verifies = summary["what_this_does_not_verify"]
    verifies_items = ""
    non_verifies_items = ""
    if isinstance(verifies, list):
        verifies_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in verifies)
    if isinstance(non_verifies, list):
        non_verifies_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in non_verifies)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>ETS Verification "
        "Certificate</title></head><body><h1>ETS Verification Certificate</h1>"
        f"<table>{rows}</table><h2>What This Verifies</h2><ul>{verifies_items}</ul>"
        f"<h2>What This Does Not Verify</h2><ul>{non_verifies_items}</ul>"
        f"<h2>Warnings</h2><ul>{warning_items}</ul></body></html>"
    )
