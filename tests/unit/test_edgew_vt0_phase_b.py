from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = (
    ROOT
    / "scripts"
    / "qualification"
    / "edgew_vt0"
    / "preflight_vt0_phase_b.sh"
)


def test_phase_b_preflight_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(PREFLIGHT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_phase_b_preflight_binds_normative_cases_and_boundaries() -> None:
    text = PREFLIGHT.read_text(encoding="utf-8")

    for case_id in (
        "EDGE-HQP-DUR-001",
        "EDGE-HQP-BPR-001",
        "EDGE-HQP-OFF-001",
        "EDGE-HQP-CHK-001",
        "EDGE-HQP-OPS-001",
    ):
        assert case_id in text

    assert "all_phase_a_cases_pass" in text
    assert "max_items=3" in text
    assert "HTTP 503 backpressure" in text
    assert "stop only edge-upstream" in text
    assert "consistency proof" in text
    assert "ETS Verifier" in text
    assert "not independent trust-anchor issuance" in text
    assert "No Docker volumes will be deleted." in text
    assert "private signing key bytes will not enter host evidence" in text
    assert "claim_state=simulated" in text
    assert "PHASE_B_PREFLIGHT_READY=true" in text


def test_phase_b_preflight_requires_external_host_verifier() -> None:
    text = PREFLIGHT.read_text(encoding="utf-8")

    assert "import ets.verifier.cli" in text
    assert "host ETS verifier runtime is unavailable" in text
    assert "do not execute OPS-001 yet" in text
