from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification" / "edgew_vt0" / "provision_vt0_dut.sh"
STORAGE_SCRIPT = (
    ROOT / "scripts" / "qualification" / "edgew_vt0" / "prepare_vt0_storage.sh"
)


def _bash_syntax_ok(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-n", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_provisioner_has_valid_bash_syntax() -> None:
    result = _bash_syntax_ok(SCRIPT)
    assert result.returncode == 0, result.stderr


def test_storage_preparer_has_valid_bash_syntax() -> None:
    result = _bash_syntax_ok(STORAGE_SCRIPT)
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


def test_storage_preparer_requires_explicit_destructive_apply() -> None:
    text = STORAGE_SCRIPT.read_text(encoding="utf-8")

    assert 'TARGET="/dev/mapper/vg_comfy-lv_comfy"' in text
    assert 'MOUNTPOINT="/srv/ets-lab"' in text
    assert "--apply" in text
    assert 'if [[ "$TARGET_REAL" == "$ROOT_REAL" ]]' in text
    assert "REFUSING: target resolves to the host root filesystem device." in text
    assert 'if [[ "$APPLY" -ne 1 ]]' in text
    assert "PLAN ONLY: no storage changes were made." in text
    assert "mkfs.ext4 -F -L ETS_LAB" in text
    assert "fstab entry (not written automatically)" in text
