from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification" / "edgew_vt0" / "provision_vt0_dut.sh"


def test_provisioner_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_provisioner_preserves_vt0_safety_and_topology_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'VCPUS=4' in text
    assert 'MEM_MIB=16384' in text
    assert 'CPUSET="0,2,4,6"' in text
    assert 'NUMA_NODE="0"' in text
    assert 'QUAL_SIZE="512G"' in text

    for network in (
        "edgew-vt-mgmt",
        "edgew-vt-source",
        "edgew-vt-upstream",
        "edgew-vt-fault",
    ):
        assert network in text

    assert "--tpm backend.type=emulator,backend.version=2.0,model=tpm-crb" in text
    assert "Ubuntu 24.04 LTS" in text
    assert "--allow-root-storage" in text
    assert 'MOUNT_TARGET" == "/"' in text
    assert "refusing overwrite" in text.lower()
    assert "not physical qualification" in text
