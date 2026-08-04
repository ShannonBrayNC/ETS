"""Human-readable verification certificate generation."""

from __future__ import annotations

import html
import json
from typing import Literal

from ets.core import EvidenceProofBundle
from ets.version import __version__

CertificateFormat = Literal["json", "markdown", "html"]

WHAT_THIS_VERIFIES = [
    "The event hash was recomputed from the provided EvidenceEvent payload.",
    "The inclusion proof verified against the stated tree head when proof_valid is true.",
    "The tree size and root matched the supplied proof material when proof_valid is true.",
    "The certificate was generated using the stated ETS verifier version.",
]

WHAT_THIS_DOES_NOT_VERIFY = [
    "This certificate does not verify election correctness.",
    "The real-world truth of the underlying evidence.",
    "The authenticity of raw evidence bytes outside ETS.",
    "The completeness of all expected evidence.",
    (
        "The identity, authority, or legal capacity of the original submitter "
        "unless separately attested."
    ),
    "The continued availability or custody of raw evidence bytes outside ETS.",
    (
        "Election correctness, vote totals, ballot validity, official results, "
        "or the vote of record."
    ),
    "Legal sufficiency, regulatory acceptance, or court admissibility.",
]


def create_certificate(
    bundle: EvidenceProofBundle,
    output_format: CertificateFormat = "json",
) -> str:
    """Create a claim-safe verification certificate without exposing raw evidence bytes."""

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
        "what_this_verifies": WHAT_THIS_VERIFIES,
        "what_this_does_not_verify": WHAT_THIS_DOES_NOT_VERIFY,
        "warnings": _warnings(bundle),
    }


def _warnings(bundle: EvidenceProofBundle) -> list[str]:
    warnings: list[str] = []
    if bundle.tree_head.signature is None:
        warnings.append("Tree head is unsigned local-mode metadata, not production trust.")
    if not bundle.verification_result.valid:
        warnings.append("Inclusion proof verification failed.")
    warnings.append(
        "Certificate verifies supplied ETS proof material only; it does not "
        "prove real-world truth, completeness, or legal sufficiency."
    )
    return warnings


def _markdown_certificate(summary: dict[str, object]) -> str:
    verifies = summary["what_this_verifies"]
    does_not_verify = summary["what_this_does_not_verify"]
    verify_items = verifies if isinstance(verifies, list) else []
    non_verify_items = does_not_verify if isinstance(does_not_verify, list) else []

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
    ]
    lines.extend(f"- {item}" for item in verify_items)

    lines.extend(
        [
            "",
            "## What This Does Not Verify",
        ]
    )
    lines.extend(f"- {item}" for item in non_verify_items)

    warnings = summary["warnings"]
    if isinstance(warnings, list) and warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def _html_list(items: object) -> str:
    if not isinstance(items, list):
        return ""
    return "".join(f"<li>{html.escape(str(item))}</li>" for item in items)


def _html_certificate(summary: dict[str, object]) -> str:
    rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in summary.items()
        if key
        not in {
            "warnings",
            "what_this_verifies",
            "what_this_does_not_verify",
        }
    )
    warning_items = _html_list(summary["warnings"])
    verifies = _html_list(summary["what_this_verifies"])
    does_not_verify = _html_list(summary["what_this_does_not_verify"])
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>ETS Verification '
        "Certificate</title></head><body><h1>ETS Verification Certificate</h1>"
        f"<table>{rows}</table>"
        f"<h2>What This Verifies</h2><ul>{verifies}</ul>"
        f"<h2>What This Does Not Verify</h2><ul>{does_not_verify}</ul>"
        f"<h2>Warnings</h2><ul>{warning_items}</ul></body></html>"
    )
