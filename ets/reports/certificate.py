"""Human-readable verification certificate generation."""

from __future__ import annotations

import html
import json
from typing import Literal

from ets import __version__
from ets.core import EvidenceProofBundle

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
        if key != "warnings"
    )
    warnings = summary["warnings"]
    warning_items = ""
    if isinstance(warnings, list):
        warning_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>ETS Verification "
        "Certificate</title></head><body><h1>ETS Verification Certificate</h1>"
        f"<table>{rows}</table><h2>Warnings</h2><ul>{warning_items}</ul></body></html>"
    )
