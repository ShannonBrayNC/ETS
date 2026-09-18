from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification" / "edgew_vt0" / "provision_vt0_dut.sh"
STORAGE_SCRIPT = (
    ROOT / "scripts" / "qualification" / "edgew_vt0" / "prepare_vt0_storage.sh"
)
REPAIR_SCRIPT = (
    ROOT / "scripts" / "qualification" / "edgew_vt0" / "repair_vt0_guest_network.sh"
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
    assert "--resume-partial" in text
    assert 'MOUNT_TARGET" == "/"' in text
    assert "refusing overwrite" in text.lower()
    assert "not physical qualification" in text
    assert "network-config=${NETWORK_CONFIG}" in text
    assert "52:54:00:97:be:12" in text
    assert "52:54:00:43:19:c6" in text
    assert "52:54:00:92:fa:95" in text
    assert "52:54:00:75:b7:33" in text
    assert "192.168.250.10/24" in text
    assert "via: 192.168.250.1" in text
    assert "192.168.251.10/24" in text
    assert "192.168.252.10/24" in text
    assert "192.168.253.10/24" in text
    assert "--dry-run" in text
    assert "--print-xml" in text
    assert "virt-install-preflight.xml" in text
    assert "virt-install.log" in text
    assert "Validated retained partial-run qcow2 disks." in text
    assert "libvirt-qemu" in text
    assert "setfacl" in text
    assert "QEMU runtime account lacks read/write access" in text
    assert "execute-only traversal on parent directories" in text
    assert 'f"u:{user}:x"' in text
    assert "QEMU runtime path traversal/stat preflight passed." in text
    assert "QEMU runtime qcow2 read/write preflight passed." in text


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



def test_guest_network_repair_has_valid_bash_syntax() -> None:
    result = _bash_syntax_ok(REPAIR_SCRIPT)
    assert result.returncode == 0, result.stderr


def test_guest_network_repair_preserves_safety_and_role_contract() -> None:
    text = REPAIR_SCRIPT.read_text(encoding="utf-8")

    assert "--apply" in text
    assert "PLAN ONLY: no guest disk or VM state was changed." in text
    assert "No force-destroy was attempted." in text
    assert "SUPERMIN_KERNEL" in text
    assert "SUPERMIN_MODULES" in text
    assert "LIBGUESTFS_BACKEND=direct" in text
    assert "Reusing retained pre-network backup" in text
    assert "virt-customize-network-repair.log" in text
    assert "netplan generate" in text
    assert "--install openssh-server" in text
    assert '--ssh-inject "ubuntu:file:$SSH_PUB"' in text
    assert "ssh-keygen -A" in text
    assert "systemctl enable ssh.socket" in text
    assert "SSH port reachable: $MGMT_IP:22" in text
    assert "qemu-img convert" in text
    assert "virt-customize" in text
    assert "rm -f /etc/netplan/50-cloud-init.yaml" in text
    assert "90-ets-vt0.yaml" in text
    assert "edgew-vt-mgmt" in text
    assert "Management address reachable: $MGMT_IP" in text
    assert "print $5; found=1" in text
    assert "print $5; exit" not in text
    assert "edgew-vt-source" in text
    assert "edgew-vt-upstream" in text
    assert "edgew-vt-fault" in text
    assert "192.168.251.10/24" in text
    assert "192.168.252.10/24" in text
    assert "192.168.253.10/24" in text
