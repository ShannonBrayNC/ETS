from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "qualification" / "edgew_vt0" / "deploy_vt0_edge_runtime.sh"
PHASE_A = ROOT / "scripts" / "qualification" / "edgew_vt0" / "capture_vt0_phase_a.sh"


def _bash_ok(path: Path) -> None:
    result = subprocess.run(
        ["bash", "-n", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_vt0_phase_a_scripts_have_valid_bash_syntax() -> None:
    _bash_ok(DEPLOY)
    _bash_ok(PHASE_A)


def test_runtime_deployment_binds_exact_build_and_qualification_storage() -> None:
    text = DEPLOY.read_text(encoding="utf-8")

    assert "git rev-parse HEAD" in text
    assert "uncommitted changes" in text
    assert "/var/lib/ets-qualification/docker" in text
    assert "/var/lib/ets-qualification/containerd" in text
    assert "growpart -N /dev/vda 1" in text
    assert "growpart-dry-run.txt" in text
    assert "No partition-table change was attempted." in text
    assert "growpart /dev/vda 1" in text
    assert "resize2fs /dev/vda1" in text
    assert "root-expansion" in text
    assert "less than 8 GiB free remains on guest root" in text
    assert "install -d -m 0755 /etc/containerd" in text
    assert "legacy-containerd-root.txt" in text
    assert "systemctl stop containerd.service" in text
    assert "docker info --format" in text
    assert "less than 100 GiB free" in text
    assert "/opt/ets/releases/$SOURCE_SHA" in text
    assert ".ets-build-commit" in text
    assert ".ets-source-archive-sha256" in text
    assert "docker compose -f edge-demo/docker-compose.yml build" in text
    assert "edge/v1/device/identity" in text
    assert "No API key or signing private-key bytes were copied" in text
    assert "Retained deployment evidence stays root-owned" in text
    assert 'sudo tee "$EVIDENCE/ready.json"' in text
    assert 'sudo tee "$EVIDENCE/version.json"' in text
    assert 'sudo tee "$EVIDENCE/device-identity.json"' in text
    assert 'sudo tee "$EVIDENCE/compose-ps.jsonl"' in text
    assert 'sudo tee "$EVIDENCE/SHA256SUMS"' in text
    assert 'ready.json" 2>/dev/null' not in text
    assert "not physical EDGE-RT0 qualification" in text


def test_phase_a_maps_to_canonical_hqp_cases_without_overclaiming() -> None:
    text = PHASE_A.read_text(encoding="utf-8")

    for case_id in (
        "EDGE-HQP-BLD-001",
        "EDGE-HQP-ID-001",
        "EDGE-HQP-SEC-001",
    ):
        assert case_id in text

    assert "edge.build-identity.v1" in text
    assert "edge.identity-enrollment.v1" in text
    assert "edge.security-posture.v1" in text
    assert "software_volume" in text
    assert "hardware_attested" in text
    assert "secret_exposure_scan_clear" in text
    assert "tpm0" in text
    assert "tpmrm0" in text
    assert "all_phase_a_cases_pass" in text
    assert "not_physical_hardware_qualification" in text
