#!/usr/bin/env bash
set -euo pipefail

GUEST_HOST="192.168.250.10"
GUEST_USER="etsadmin"
SSH_KEY="${HOME}/.ssh/edgew_vt0"
BASELINE_ROOT="/srv/ets-lab/evidence/vt0-guest-baseline"
OUT_ROOT="/srv/ets-lab/evidence/vt0-qualification-disk-init"
APPLY=0

usage() {
  cat <<'EOF'
Usage:
  initialize_vt0_qualification_disk.sh [--host IP] [--user USER]
                                       [--ssh-key PATH]
                                       [--baseline-root PATH]
                                       [--out-root PATH] [--apply]

Plan-only by default. --apply is required before /dev/vdb is partitioned or
formatted. A passing pristine guest baseline is mandatory.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) GUEST_HOST="${2:?missing value for --host}"; shift 2 ;;
    --user) GUEST_USER="${2:?missing value for --user}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?missing value for --ssh-key}"; shift 2 ;;
    --baseline-root) BASELINE_ROOT="${2:?missing value for --baseline-root}"; shift 2 ;;
    --out-root) OUT_ROOT="${2:?missing value for --out-root}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in ssh python3 date sha256sum find; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
done

[[ -r "$SSH_KEY" ]] || {
  echo "ERROR: SSH private key not readable: $SSH_KEY" >&2
  exit 2
}

LATEST_BASELINE="$(
  find "$BASELINE_ROOT" -mindepth 1 -maxdepth 1 -type d     -name 'edgew-rt0-vt0-dut-*' -printf '%T@ %p\n' 2>/dev/null   | sort -nr | head -1 | cut -d' ' -f2-
)"

[[ -n "$LATEST_BASELINE" && -f "$LATEST_BASELINE/guest-baseline-summary.json" ]] || {
  echo "ERROR: no pristine VT0 guest baseline found under $BASELINE_ROOT" >&2
  exit 2
}

python3 - "$LATEST_BASELINE/guest-baseline-summary.json" <<'PY'
import json
from pathlib import Path
import sys

summary = json.loads(Path(sys.argv[1]).read_text())
if summary.get("all_pristine_checks_pass") is not True:
    raise SystemExit("ERROR: latest pristine guest baseline did not pass all checks")
if summary.get("qualification_disk_target") != "/dev/vdb":
    raise SystemExit("ERROR: baseline qualification disk target is not /dev/vdb")
print("Pristine baseline gate passed.")
PY

SSH=(
  ssh
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=5
  -i "$SSH_KEY"
  "${GUEST_USER}@${GUEST_HOST}"
)

"${SSH[@]}" 'sudo -n true' || {
  echo "ERROR: guest sudo preflight failed" >&2
  exit 2
}

PLAN="$(
  "${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
TARGET=/dev/vdb
EXPECTED=$((512 * 1024 * 1024 * 1024))

[[ -b "$TARGET" ]] || { echo "ERROR: $TARGET is not a block device" >&2; exit 3; }
SIZE="$(sudo blockdev --getsize64 "$TARGET")"
[[ "$SIZE" -eq "$EXPECTED" ]] || {
  echo "ERROR: $TARGET size is $SIZE, expected $EXPECTED" >&2
  exit 3
}

ROOT_SOURCE="$(findmnt -n -o SOURCE /)"
ROOT_PARENT="$(lsblk -no PKNAME "$ROOT_SOURCE" 2>/dev/null || true)"
if [[ "$ROOT_SOURCE" == "$TARGET" || "$ROOT_PARENT" == "vdb" ]]; then
  echo "ERROR: target overlaps guest root filesystem" >&2
  exit 3
fi

mapfile -t TREE < <(lsblk -nrpo NAME,TYPE "$TARGET")
[[ "${#TREE[@]}" -eq 1 ]] || {
  echo "ERROR: $TARGET already has partitions/children" >&2
  printf '%s\n' "${TREE[@]}" >&2
  exit 3
}

SIGS="$(sudo wipefs -n "$TARGET")"
[[ -z "$SIGS" ]] || {
  echo "ERROR: $TARGET already has filesystem/partition signatures" >&2
  echo "$SIGS" >&2
  exit 3
}

MOUNTS="$(lsblk -nro MOUNTPOINTS "$TARGET" | sed '/^[[:space:]]*$/d')"
[[ -z "$MOUNTS" ]] || {
  echo "ERROR: $TARGET has mounted content" >&2
  echo "$MOUNTS" >&2
  exit 3
}

echo "VT0 qualification-disk initialization plan"
echo "  target:       $TARGET"
echo "  exact size:   $SIZE bytes (512 GiB)"
echo "  current state: blank, unpartitioned, unmounted"
echo "  partitioning: GPT, one Linux filesystem partition"
echo "  filesystem:   ext4, label ETS_QUAL"
echo "  mountpoint:   /var/lib/ets-qualification"
echo "  persistence:  UUID-bound /etc/fstab entry, defaults,noatime"
REMOTE
)"

printf '%s\n' "$PLAN"

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "PLAN ONLY: /dev/vdb was not modified."
  echo "Re-run with --apply only after reviewing the plan."
  exit 0
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_ROOT}/edgew-rt0-vt0-dut-${TS}"
mkdir -p "$OUT_DIR"
printf '%s\n' "$PLAN" >"$OUT_DIR/plan.txt"
cp "$LATEST_BASELINE/guest-baseline-summary.json" "$OUT_DIR/pristine-baseline-summary.json"
cp "$LATEST_BASELINE/SHA256SUMS" "$OUT_DIR/pristine-baseline-SHA256SUMS"

"${SSH[@]}" 'bash -s' >"$OUT_DIR/apply.txt" 2>&1 <<'REMOTE'
set -euo pipefail
TARGET=/dev/vdb
PART=/dev/vdb1
EXPECTED=$((512 * 1024 * 1024 * 1024))
MOUNTPOINT=/var/lib/ets-qualification

[[ -b "$TARGET" ]] || { echo "ERROR: target missing" >&2; exit 3; }
[[ "$(sudo blockdev --getsize64 "$TARGET")" -eq "$EXPECTED" ]] || {
  echo "ERROR: target size changed" >&2
  exit 3
}
[[ "$(lsblk -nrpo NAME,TYPE "$TARGET" | wc -l)" -eq 1 ]] || {
  echo "ERROR: target is no longer pristine" >&2
  exit 3
}
[[ -z "$(sudo wipefs -n "$TARGET")" ]] || {
  echo "ERROR: target gained signatures after baseline" >&2
  exit 3
}

echo 'label: gpt' | sudo sfdisk "$TARGET"
echo ',,L' | sudo sfdisk --append "$TARGET"
sudo udevadm settle

[[ -b "$PART" ]] || {
  echo "ERROR: expected partition $PART did not appear" >&2
  exit 4
}

sudo mkfs.ext4 -F -L ETS_QUAL -m 0 "$PART"
sudo install -d -m 0750 -o root -g root "$MOUNTPOINT"

UUID="$(sudo blkid -s UUID -o value "$PART")"
PARTUUID="$(sudo blkid -s PARTUUID -o value "$PART")"

sudo cp /etc/fstab "/etc/fstab.pre-ets-qual-$(date -u +%Y%m%dT%H%M%SZ)"
if ! sudo grep -q "UUID=${UUID}[[:space:]]" /etc/fstab; then
  echo "UUID=${UUID} ${MOUNTPOINT} ext4 defaults,noatime 0 2"     | sudo tee -a /etc/fstab >/dev/null
fi

sudo mount "$MOUNTPOINT"

echo "qualification_disk=/dev/vdb"
echo "qualification_partition=$PART"
echo "filesystem_uuid=$UUID"
echo "partition_uuid=$PARTUUID"
echo "mountpoint=$MOUNTPOINT"
echo
lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,PARTUUID,MOUNTPOINTS "$TARGET"
echo
findmnt "$MOUNTPOINT"
echo
df -hT "$MOUNTPOINT"
REMOTE

"${SSH[@]}" "lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,PARTUUID,MOUNTPOINTS /dev/vdb"   >"$OUT_DIR/post-lsblk.json"
"${SSH[@]}" "sudo blkid /dev/vdb /dev/vdb1"   >"$OUT_DIR/post-blkid.txt"
"${SSH[@]}" "findmnt /var/lib/ets-qualification -o TARGET,SOURCE,FSTYPE,SIZE,AVAIL,OPTIONS"   >"$OUT_DIR/post-findmnt.txt"
"${SSH[@]}" "sudo cat /etc/fstab"   >"$OUT_DIR/post-fstab.txt"

python3 - "$OUT_DIR" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
data = json.loads((out / "post-lsblk.json").read_text())
vdb = data["blockdevices"][0]
children = vdb.get("children") or []
part = children[0] if children else {}

checks = {
    "vdb_size_512_gib": vdb.get("size") == 512 * 1024**3,
    "single_partition": len(children) == 1 and part.get("name") == "vdb1",
    "ext4_filesystem": part.get("fstype") == "ext4",
    "filesystem_label": part.get("label") == "ETS_QUAL",
    "filesystem_uuid_present": bool(part.get("uuid")),
    "partition_uuid_present": bool(part.get("partuuid")),
    "mounted_at_expected_path": "/var/lib/ets-qualification"
        in (part.get("mountpoints") or []),
}
summary = {
    "schema": "ets.edgew.vt0.qualification-disk-init.v1",
    "claim_state": "simulated",
    "checks": checks,
    "all_initialization_checks_pass": all(checks.values()),
    "claim_boundary": (
        "vt0_qualification_storage_initialization_only_not_physical_endurance_"
        "power_loss_truth_completeness_compliance_safety_or_production_readiness"
    ),
}
(out / "qualification-disk-init-summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps(summary, indent=2))
PY

(
  cd "$OUT_DIR"
  find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name SHA256SUMS.verify.txt -printf '%P\n'     | sort     | xargs -r sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS > SHA256SUMS.verify.txt
)

chmod -R go-rwx "$OUT_DIR"

echo
echo "Qualification disk initialized and evidence retained: $OUT_DIR"
echo "Summary: $OUT_DIR/qualification-disk-init-summary.json"
echo "This establishes only simulated VT0 storage setup, not physical qualification."
