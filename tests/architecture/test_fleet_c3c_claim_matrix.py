from __future__ import annotations

from pathlib import Path

MATRIX = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "fleet"
    / "ETS_FLEET_C3C_CLAIM_MATRIX.md"
)


def test_c3c_initial_claim_matrix_never_equates_implementation_with_live_evidence() -> None:
    source = MATRIX.read_text(encoding="utf-8")
    assert "Live evidence, not implementation presence, advances the claims." in source
    assert "No row may be advanced merely because a Bicep template" in source
    assert "`shared_store_qualified` | False" in source
    assert "`entra_enforced` | False" in source
    assert "`public_hostname_tls_qualified` | False" in source
    assert "`live_fleet_mutation_qualified` | False" in source
    assert "apex and current `www` records are not modified" in source
