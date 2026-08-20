from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVISIONER = (
    ROOT / "scripts" / "m365" / "provision-echomedia-sharepoint-connector.ps1"
).read_text(encoding="utf-8")


def test_provisioner_graph_site_query_braces_variables_before_question_mark() -> None:
    assert 'sites/${SharePointHostname}:${SitePath}?' in PROVISIONER
    assert "$SitePath?" not in PROVISIONER
