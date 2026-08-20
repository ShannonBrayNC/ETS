from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPERATOR = (
    ROOT / "scripts" / "m365" / "create-echomedia-sharepoint-qualification-document.ps1"
).read_text(encoding="utf-8")


def test_graph_query_variables_are_braced_before_question_mark() -> None:
    assert 'sites/${SharePointHostname}:${SitePath}?' in OPERATOR
    assert 'root:/${encodedName}?' in OPERATOR
    assert "$SitePath?" not in OPERATOR
    assert "$encodedName?" not in OPERATOR
