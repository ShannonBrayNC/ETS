# scripts/apply-ets-certificate-claim-safety-sprint.ps1
# Purpose: Complete ETS sprint recommendation:
# Update certificate wording to avoid overclaiming and harden verifier/certificate version imports.
# Run from the root of ShannonBrayNC/ETS with PowerShell 7+.

[CmdletBinding()]
param(
    [switch]$SkipChecks,
    [switch]$SkipTag
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-RepoRoot {
    if (-not (Test-Path "README.md") -or -not (Test-Path "ets") -or -not (Test-Path "docs")) {
        throw "Run this script from the root of the ETS repository."
    }
}

function Write-Utf8NoNewline {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    Set-Content -Path $Path -Value $Content -Encoding UTF8 -NoNewline
    Write-Host "Wrote $Path"
}

function Update-FileText {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][scriptblock]$Transform
    )

    if (-not (Test-Path $Path)) {
        throw "Required file not found: $Path"
    }

    $original = Get-Content -Raw -Path $Path
    $updated = & $Transform $original

    if ($null -eq $updated -or $updated.Length -eq 0) {
        throw "Transform produced empty content for $Path"
    }

    if ($updated -ne $original) {
        Set-Content -Path $Path -Value $updated -Encoding UTF8 -NoNewline
        Write-Host "Updated $Path"
    }
    else {
        Write-Host "No change needed $Path"
    }
}

Assert-RepoRoot

# 1. Centralize version resolution so console scripts do not depend on `from ets import __version__`.
$versionPy = @'
"""Version helpers for ETS."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed ETS package version with a source-tree fallback."""

    try:
        return version("ets")
    except PackageNotFoundError:  # pragma: no cover - source tree before install
        return "0.1.0"


__version__ = get_version()

__all__ = ["__version__", "get_version"]
'@

Write-Utf8NoNewline -Path "ets/version.py" -Content $versionPy

# 2. Ensure package __init__ delegates to version helper.
$initPy = @'
"""Evidence Transparency System package."""

from ets.version import __version__

__all__ = ["__version__", "api", "core", "verifier"]
'@

Write-Utf8NoNewline -Path "ets/__init__.py" -Content $initPy

# 3. If src/ets exists in the working tree, make it safe too.
if (Test-Path "src/ets") {
    Write-Utf8NoNewline -Path "src/ets/version.py" -Content $versionPy
    Write-Utf8NoNewline -Path "src/ets/__init__.py" -Content $initPy
}

# 4. Update CLI version import.
Update-FileText -Path "ets/verifier/cli.py" -Transform {
    param($text)

    $text = $text -replace "from ets import __version__", "from ets.version import __version__"
    return $text
}

# 5. Replace certificate generator with claim-safe implementation.
$certificatePy = @'
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
    "The real-world truth of the underlying evidence.",
    "The authenticity of raw evidence bytes outside ETS.",
    "The completeness of all expected evidence.",
    "The identity, authority, or legal capacity of the original submitter unless separately attested.",
    "The continued availability or custody of raw evidence bytes outside ETS.",
    "Election correctness, vote totals, ballot validity, official results, or the vote of record.",
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
        "Certificate verifies supplied ETS proof material only; it does not prove real-world truth, completeness, or legal sufficiency."
    )
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
        "",
        "## What This Verifies",
    ]

    verifies = summary["what_this_verifies"]
    if isinstance(verifies, list):
        lines.extend(f"- {item}" for item in verifies)

    lines.extend(
        [
            "",
            "## What This Does Not Verify",
        ]
    )

    does_not_verify = summary["what_this_does_not_verify"]
    if isinstance(does_not_verify, list):
        lines.extend(f"- {item}" for item in does_not_verify)

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
'@

Write-Utf8NoNewline -Path "ets/reports/certificate.py" -Content $certificatePy

# 6. Add certificate claim-safety documentation.
$claimDoc = @'
# ETS Certificate Claim Safety

ETS verification certificates are protocol verification reports. They are not legal opinions, official records, or assertions that the underlying real-world event is true.

## Required Certificate Sections

Every human-readable certificate format must include:

- `What This Verifies`
- `What This Does Not Verify`
- `Warnings` when any local-mode, unsigned, failed, or claim-boundary condition applies

JSON certificates must include:

- `what_this_verifies`
- `what_this_does_not_verify`
- `warnings`

## What Certificates May Claim

Certificates may claim that ETS reproduced protocol-level checks from supplied proof material:

- event hash reproduction;
- inclusion proof verification;
- tree-head field reporting;
- signature presence reporting;
- verifier version reporting;
- warnings and claim boundaries.

## What Certificates Must Not Claim

Certificates must not claim:

- real-world truth;
- raw evidence authenticity;
- evidence completeness;
- submitter legal authority;
- election correctness;
- vote totals, ballot validity, official results, or vote of record;
- legal sufficiency, regulatory acceptance, or court admissibility.

## Required Regression Checks

The certificate source, tests, and verifier CLI must prevent reintroduction of:

``

'@