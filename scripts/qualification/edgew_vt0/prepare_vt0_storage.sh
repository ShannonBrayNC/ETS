#!/usr/bin/env bash
set -euo pipefail

TARGET="/dev/mapper/vg_comfy-lv_comfy"
MOUNTPOINT="/srv/ets-lab"
APPLY=0

usage() {
  cat <<'EOF'
Usage:
  prepare_vt0_storage.sh [--target DEVICE] [--mountpoint PATH] [--apply]

Default behavior is plan-only. --apply is required before formatting.

This script is intentionally destructive only when --apply is supplied.
It refuses to operate on the host root filesystem and refuses unexpected mounts.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:?missing value for --target}"
      shift 2
      ;;
    --mountpoint)
      MOUNTPOINT="${2:?missing value for --mountpoint}"
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as the normal operator account; sudo will be used where needed." >&2
  exit 2
fi

for cmd in findmnt lsblk blkid readlink mkfs.ext4 mount umount install; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Required command not found: $cmd" >&2
    exit 2
  }
done

if [[ ! -b "$TARGET" ]]; then
  echo "Target is not a block device: $TARGET" >&2
  exit 2
fi

TARGET_REAL="$(readlink -f "$TARGET")"
ROOT_SOURCE="$(findmnt -n -o SOURCE /)"
ROOT_REAL="$(readlink -f "$ROOT_SOURCE" 2>/dev/null || printf '%s' "$ROOT_SOURCE")"

if [[ "$TARGET_REAL" == "$ROOT_REAL" ]]; then
  echo "REFUSING: target resolves to the host root filesystem device." >&2
  exit 3
fi

echo "VT0 storage preparation plan"
echo "  target:      $TARGET ($TARGET_REAL)"
echo "  mountpoint:  $MOUNTPOINT"
echo "  action:      DESTROY existing filesystem contents, create ext4 label ETS_LAB, mount for VT0"
echo

echo "Current block-device identity:"
lsblk -f "$TARGET" || true
sudo blkid "$TARGET" || true
echo

mapfile -t MOUNTS < <(findmnt -rn -S "$TARGET" -o TARGET || true)
for m in "${MOUNTS[@]:-}"; do
  [[ -z "$m" ]] && continue
  if [[ "$m" == "/mnt/ets-comfy-inspect" ]]; then
    echo "Known read-only inspection mount detected at $m."
  else
    echo "REFUSING: target is mounted at unexpected path: $m" >&2
    exit 3
  fi
done

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "PLAN ONLY: no storage changes were made."
  echo "Re-run with --apply only after confirming this is the disposable old-content volume."
  exit 0
fi

for m in "${MOUNTS[@]:-}"; do
  [[ -z "$m" ]] && continue
  if [[ "$m" == "/mnt/ets-comfy-inspect" ]]; then
    sudo umount "$m"
  fi
done

if findmnt -rn -S "$TARGET" >/dev/null 2>&1; then
  echo "REFUSING: target remains mounted after inspection unmount attempt." >&2
  exit 3
fi

echo "Formatting $TARGET as ext4 (label ETS_LAB)..."
sudo mkfs.ext4 -F -L ETS_LAB "$TARGET"

sudo install -d -m 0750 -o "$USER" -g libvirt "$MOUNTPOINT"
sudo mount "$TARGET" "$MOUNTPOINT"
sudo chown "$USER":libvirt "$MOUNTPOINT"
sudo chmod 0750 "$MOUNTPOINT"

UUID="$(sudo blkid -s UUID -o value "$TARGET")"
echo
echo "Storage prepared and mounted."
findmnt "$MOUNTPOINT" -o TARGET,SOURCE,FSTYPE,SIZE,AVAIL,OPTIONS
echo
echo "Filesystem UUID: $UUID"
echo "Suggested persistent fstab entry (not written automatically):"
echo "UUID=$UUID $MOUNTPOINT ext4 defaults,noatime 0 2"
echo
echo "Next: run provision_vt0_dut.sh with --storage-root $MOUNTPOINT in plan mode."
