from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "scripts" / "qualification" / "edgew_vt0" / "capture_vt0_guest_baseline.sh"
INIT = ROOT / "scripts" / "qualification" / "edgew_vt0" / "initialize_vt0_qualification_disk.sh"


def _bash_ok(path: Path) -> None:
    result = subprocess.run(["bash", "-n", str(path)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_guest_baseline_scripts_have_valid_bash_syntax() -> None:
    _bash_ok(CAPTURE)
    _bash_ok(INIT)


def test_pristine_guest_baseline_contract() -> None:
    text = CAPTURE.read_text()
    assert "192.168.250.10" in text
    assert "etsadmin" in text
    assert "qualification_disk_target" in text
    assert '"/dev/vdb"' in text
    assert "512 * 1024**3" in text
    assert "qualification_disk_has_no_wipefs_signatures" in text
    assert "tpm0_present" in text
    assert "tpmrm0_present" in text
    assert "all_pristine_checks_pass" in text
    assert "SHA256SUMS.verify.txt" in text
    assert "not_physical_hardware_qualification" in text


def test_qualification_disk_initializer_is_guarded() -> None:
    text = INIT.read_text()
    assert "--apply" in text
    assert "PLAN ONLY: /dev/vdb was not modified." in text
    assert "all_pristine_checks_pass" in text
    assert "TARGET=/dev/vdb" in text
    assert "EXPECTED=$((512 * 1024 * 1024 * 1024))" in text
    assert "target overlaps guest root filesystem" in text
    assert "target gained signatures after baseline" in text
    assert "label: gpt" in text
    assert "mkfs.ext4 -F -L ETS_QUAL -m 0" in text
    assert "/var/lib/ets-qualification" in text
    assert "fstab.pre-ets-qual" in text
    assert "all_initialization_checks_pass" in text
    assert "not_physical_endurance" in text
