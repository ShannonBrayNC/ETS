"""Render a fresh offline verification outcome, never a bundle's claimed result."""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ets.reports.certificate import CertificateFormat
from ets.version import __version__

LIMITATIONS = [
    "Offline verification evaluates supplied material at a checkpoint, not the current log state.",
    "Trust is relative to the supplied out-of-band trust store and recorded policy.",
    "Current revocation, freshness, or authorization cannot be established offline.",
    "No claim is made about real-world truth, completeness, or legal sufficiency.",
    "This report is an unsigned observation, not a signed proof or replacement evidence bundle.",
]


def write_new_report(path: Path, content: str) -> None:
    """Publish a complete file without replacing any existing destination."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=".ets-report-",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        # Same-directory hard link is atomic and fails if the destination exists.
        # A filesystem without hard-link support fails closed rather than overwriting.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def render_offline_report(
    outcome: dict[str, Any],
    *,
    require_signature: bool,
    expected_log_id: str | None,
    output_format: CertificateFormat = "json",
) -> str:
    """Preserve the computed outcome verbatim within a versioned report envelope."""
    report = {
        "schema_version": "ets.offline_report.v1",
        "verifier_version": __version__,
        "policy": {
            "require_tree_head_signature": require_signature,
            "expected_log_id": expected_log_id,
            "trust_source": "external_verifier_trust_store",
        },
        "development_unsigned_policy": not require_signature,
        "outcome": outcome,
        "limitations": LIMITATIONS,
    }
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True)
    if output_format == "json":
        return payload + "\n"
    if output_format == "markdown":
        # A malicious identifier must not close the code fence and inject Markdown.
        longest = max((len(x) for x in re.findall(r"`+", payload)), default=0)
        fence = "`" * max(3, longest + 1)
        return (
            "# ETS Offline Verification Report\n\n"
            + fence
            + "json\n"
            + payload
            + "\n"
            + fence
            + "\n"
        )
    if output_format == "html":
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'">'
            "<title>ETS Offline Verification Report</title></head><body>"
            "<h1>ETS Offline Verification Report</h1><pre>"
            + html.escape(payload)
            + "</pre></body></html>\n"
        )
    raise ValueError("unsupported report format")
