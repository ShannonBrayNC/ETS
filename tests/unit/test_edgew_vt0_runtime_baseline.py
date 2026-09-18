from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "qualification"
    / "edgew_vt0"
    / "capture_vt0_runtime_baseline.sh"
)


def test_vt0_runtime_capture_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_vt0_runtime_capture_preserves_baseline_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "edgew-rt0-vt0-dut" in text
    assert "edgew-vt-mgmt" in text
    assert "edgew-vt-source" in text
    assert "edgew-vt-upstream" in text
    assert "edgew-vt-fault" in text
    assert "expected_cpuset = {0, 2, 4, 6}" in text
    assert "cpu_cpuset_matches_baseline" in text
    assert "runtime_cpu_affinity_bounded_to_cpuset" in text
    assert "16 * 1024 * 1024" in text
    assert "64 * 1024**3" in text
    assert "512 * 1024**3" in text
    assert "tpm-crb" in text
    assert "tpm_2_0_present" in text
    assert "management_dhcp_lease_observed" in text
    assert "SHA256SUMS" in text
    assert "SHA256SUMS.verify.txt" in text
    assert "domstate-reason.txt" in text
    assert '"claim_state": "simulated"' in text
    assert "not_physical_hardware_qualification" in text
