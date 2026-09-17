#!/usr/bin/env bash
set -euo pipefail

# Provision the EDGEW-RT0-VT0 virtual DUT on a dedicated KVM/libvirt host.
# Safe default: plan only. Use --apply with an explicit non-root storage path.
# This provisions simulated VT0 infrastructure only; it does not establish
# physical EDGE-RT0 hardware qualification.

VM_NAME="edgew-rt0-vt0-dut"
MEM_MIB=16384
VCPUS=4
CPUSET="0,2,4,6"
NUMA_NODE="0"
OS_SIZE="64G"
QUAL_SIZE="512G"
STORAGE_ROOT=""
BASE_IMAGE=""
SSH_KEY=""
APPLY=0
ALLOW_ROOT_STORAGE=0
RESUME_PARTIAL=0

usage() {
  cat <<'EOF'
Usage:
  provision_vt0_dut.sh --storage-root PATH [options]

Required:
  --storage-root PATH      Existing directory on non-root storage for VT0 disks

Options:
  --base-image PATH        Existing Ubuntu 24.04 cloud image; otherwise download/verify
  --ssh-key PATH           SSH public key; default ~/.ssh/edgew_vt0.pub (created if absent)
  --cpuset LIST            Host CPU set; default 0,2,4,6
  --numa-node N            Host NUMA node; default 0
  --apply                  Create disks and define/start the VM
  --resume-partial         Reuse validated existing VT0 disks after a prior partial run
  --allow-root-storage     Explicitly allow storage rooted on / (not recommended)
  -h, --help               Show help

Without --apply this command validates prerequisites and prints the plan only.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --storage-root) STORAGE_ROOT="${2:-}"; shift 2 ;;
    --base-image) BASE_IMAGE="${2:-}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:-}"; shift 2 ;;
    --cpuset) CPUSET="${2:-}"; shift 2 ;;
    --numa-node) NUMA_NODE="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --resume-partial) RESUME_PARTIAL=1; shift ;;
    --allow-root-storage) ALLOW_ROOT_STORAGE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "${STORAGE_ROOT}" ]]; then
  echo "ERROR: --storage-root is required." >&2
  echo "Use the confirmed mounted data filesystem, not the host root filesystem." >&2
  exit 2
fi

for cmd in virsh virt-install qemu-img python3 findmnt ssh-keygen getent setfacl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: required command not found: $cmd" >&2; exit 2; }
done

if ! virsh --connect qemu:///system list --all >/dev/null 2>&1; then
  echo "ERROR: cannot access qemu:///system as the current operator." >&2
  exit 2
fi

for net in edgew-vt-mgmt edgew-vt-source edgew-vt-upstream edgew-vt-fault; do
  state="$(virsh --connect qemu:///system net-info "$net" 2>/dev/null | awk -F: '/^Active:/ {gsub(/^[ \t]+/,"",$2); print $2}')"
  if [[ "$state" != "yes" ]]; then
    echo "ERROR: required libvirt network is not active: $net" >&2
    exit 2
  fi
done

if virsh --connect qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
  echo "ERROR: domain already exists: $VM_NAME" >&2
  echo "This provisioner will not overwrite an existing VT0 domain." >&2
  exit 2
fi

IFS=',' read -r -a cpus <<<"${CPUSET}"
if [[ "${#cpus[@]}" -ne "$VCPUS" ]]; then
  echo "ERROR: --cpuset must contain exactly ${VCPUS} host CPUs." >&2
  exit 2
fi

node_path="/sys/devices/system/node/node${NUMA_NODE}/cpulist"
if [[ ! -r "$node_path" ]]; then
  echo "ERROR: NUMA node ${NUMA_NODE} does not exist on this host." >&2
  exit 2
fi
node_cpulist="$(<"$node_path")"
python3 - "$node_cpulist" "$CPUSET" <<'PY'
import sys

def expand(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = map(int, part.split('-', 1))
            out.update(range(a, b + 1))
        else:
            out.add(int(part))
    return out

node = expand(sys.argv[1])
requested = expand(sys.argv[2])
if not requested <= node:
    raise SystemExit(
        f"requested CPUs {sorted(requested)} are not contained in NUMA node CPUs {sorted(node)}"
    )
PY

if [[ ! -d "$STORAGE_ROOT" ]]; then
  echo "ERROR: storage root does not exist: $STORAGE_ROOT" >&2
  exit 2
fi
STORAGE_ROOT="$(readlink -f "$STORAGE_ROOT")"
MOUNT_TARGET="$(findmnt -T "$STORAGE_ROOT" -n -o TARGET)"
MOUNT_SOURCE="$(findmnt -T "$STORAGE_ROOT" -n -o SOURCE)"
if [[ "$MOUNT_TARGET" == "/" && "$ALLOW_ROOT_STORAGE" -ne 1 ]]; then
  echo "ERROR: $STORAGE_ROOT resolves to the host root filesystem ($MOUNT_SOURCE)." >&2
  echo "Refusing because DSK/capacity rehearsal must not threaten host recovery." >&2
  echo "Use the mounted data filesystem, or explicitly pass --allow-root-storage for non-destructive setup only." >&2
  exit 2
fi

VM_DIR="${STORAGE_ROOT}/${VM_NAME}"
CACHE_DIR="${STORAGE_ROOT}/cloud-images"
OS_DISK="${VM_DIR}/${VM_NAME}-os.qcow2"
QUAL_DISK="${VM_DIR}/${VM_NAME}-qualification.qcow2"
DEFAULT_IMAGE="${CACHE_DIR}/noble-server-cloudimg-amd64.img"

QEMU_RUNTIME_USER=""
for candidate in libvirt-qemu qemu; do
  if getent passwd "$candidate" >/dev/null 2>&1; then
    QEMU_RUNTIME_USER="$candidate"
    break
  fi
done
if [[ -z "$QEMU_RUNTIME_USER" ]]; then
  echo "ERROR: could not resolve the host QEMU runtime account (tried libvirt-qemu, qemu)." >&2
  echo "Inspect /etc/libvirt/qemu.conf and the libvirt package runtime identity before continuing." >&2
  exit 2
fi
QEMU_RUNTIME_UID="$(id -u "$QEMU_RUNTIME_USER")"
QEMU_RUNTIME_GID="$(id -g "$QEMU_RUNTIME_USER")"
QEMU_RUNTIME_GROUP="$(id -gn "$QEMU_RUNTIME_USER")"
IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
SUMS_URL="https://cloud-images.ubuntu.com/noble/current/SHA256SUMS"

if [[ -z "$SSH_KEY" ]]; then
  SSH_KEY="${HOME}/.ssh/edgew_vt0.pub"
fi

cat <<EOF
EDGEW-RT0-VT0 DUT provisioning plan
  domain:              ${VM_NAME}
  RAM:                 ${MEM_MIB} MiB
  vCPU:                ${VCPUS}
  host cpuset:         ${CPUSET}
  host NUMA node:      ${NUMA_NODE}
  storage root:        ${STORAGE_ROOT}
  filesystem source:   ${MOUNT_SOURCE}
  OS disk:             ${OS_DISK} (${OS_SIZE})
  qualification disk:  ${QUAL_DISK} (${QUAL_SIZE}, sparse)
  firmware:            UEFI/OVMF
  TPM:                 swtpm TPM 2.0 / CRB
  guest:               Ubuntu 24.04 LTS amd64 cloud image
  networks:            mgmt, source, upstream, fault
  QEMU runtime:        ${QEMU_RUNTIME_USER} (uid ${QEMU_RUNTIME_UID}, gid ${QEMU_RUNTIME_GID}/${QEMU_RUNTIME_GROUP})
  claim state:         simulated VT0 only; not physical qualification
EOF

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "PLAN ONLY: rerun with --apply after reviewing the storage path and topology."
  exit 0
fi

mkdir -p "$VM_DIR" "$CACHE_DIR"

# The system libvirt QEMU process runs as a non-root service account. Grant
# execute-only traversal on parent directories when needed, then read/write
# access only to the ETS datastore/VM path. Do not make these paths globally
# writable.
python3 - "$STORAGE_ROOT" "$QEMU_RUNTIME_USER" <<'PY'
from pathlib import Path
import subprocess
import sys

storage = Path(sys.argv[1]).resolve()
user = sys.argv[2]

# Walk from / down to the parent of the storage root. If the QEMU account
# cannot traverse a component, add only an execute ACL for that user.
current = Path("/")
for part in storage.parts[1:-1]:
    current /= part
    probe = subprocess.run(
        ["sudo", "-u", user, "test", "-x", str(current)],
        check=False,
    )
    if probe.returncode != 0:
        subprocess.run(
            ["sudo", "setfacl", "-m", f"u:{user}:x", str(current)],
            check=True,
        )
PY

sudo setfacl -m "u:${QEMU_RUNTIME_USER}:rx" "$STORAGE_ROOT"
sudo setfacl -m "u:${QEMU_RUNTIME_USER}:rwx" "$VM_DIR"
sudo setfacl -m "d:u:${QEMU_RUNTIME_USER}:rwx" "$VM_DIR"

if ! sudo -u "$QEMU_RUNTIME_USER" test -x "$STORAGE_ROOT"; then
  echo "ERROR: QEMU runtime account still cannot traverse storage root: $STORAGE_ROOT" >&2
  namei -l "$STORAGE_ROOT" >&2 || true
  getfacl -p "$STORAGE_ROOT" >&2 || true
  exit 2
fi

if [[ ! -f "$SSH_KEY" ]]; then
  if [[ "$SSH_KEY" != "${HOME}/.ssh/edgew_vt0.pub" ]]; then
    echo "ERROR: specified SSH public key does not exist: $SSH_KEY" >&2
    exit 2
  fi
  mkdir -p "${HOME}/.ssh"
  chmod 700 "${HOME}/.ssh"
  ssh-keygen -q -t ed25519 -N '' -f "${HOME}/.ssh/edgew_vt0"
fi

if [[ -n "$BASE_IMAGE" ]]; then
  BASE_IMAGE="$(readlink -f "$BASE_IMAGE")"
  [[ -f "$BASE_IMAGE" ]] || { echo "ERROR: base image not found: $BASE_IMAGE" >&2; exit 2; }
else
  BASE_IMAGE="$DEFAULT_IMAGE"
  if [[ ! -f "$BASE_IMAGE" ]]; then
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "${tmpdir:-}"' EXIT
    python3 - "$IMAGE_URL" "$SUMS_URL" "$tmpdir" <<'PY'
from pathlib import Path
from urllib.request import urlopen
import hashlib
import sys

image_url, sums_url, td = sys.argv[1:]
td = Path(td)
image_name = image_url.rsplit('/', 1)[-1]
image_path = td / image_name
sums_path = td / 'SHA256SUMS'

with urlopen(sums_url) as r, sums_path.open('wb') as f:
    f.write(r.read())
with urlopen(image_url) as r, image_path.open('wb') as f:
    while True:
        chunk = r.read(1024 * 1024)
        if not chunk:
            break
        f.write(chunk)

expected = None
for line in sums_path.read_text().splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[-1].lstrip('*') == image_name:
        expected = fields[0]
        break
if not expected:
    raise SystemExit(f"checksum entry missing for {image_name}")

h = hashlib.sha256()
with image_path.open('rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
        h.update(chunk)
actual = h.hexdigest()
if actual != expected:
    raise SystemExit(f"SHA256 mismatch: expected {expected}, got {actual}")
print(image_path)
PY
    mv "${tmpdir}/noble-server-cloudimg-amd64.img" "$BASE_IMAGE"
    rm -rf "$tmpdir"
    trap - EXIT
  fi
fi

existing_os=0
existing_qual=0
[[ -e "$OS_DISK" ]] && existing_os=1
[[ -e "$QUAL_DISK" ]] && existing_qual=1

if [[ "$existing_os" -eq 1 || "$existing_qual" -eq 1 ]]; then
  if [[ "$RESUME_PARTIAL" -ne 1 ]]; then
    echo "ERROR: target disk already exists; refusing overwrite." >&2
    echo "If this is the retained output of a prior partial VT0 run, inspect it and rerun with --resume-partial." >&2
    exit 2
  fi
  if [[ "$existing_os" -ne 1 || "$existing_qual" -ne 1 ]]; then
    echo "ERROR: --resume-partial requires both expected VT0 disks to exist." >&2
    exit 2
  fi

  python3 - "$OS_DISK" "$QUAL_DISK" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

expected = {
    Path(sys.argv[1]): 64 * 1024**3,
    Path(sys.argv[2]): 512 * 1024**3,
}
for path, expected_size in expected.items():
    result = subprocess.run(
        ["qemu-img", "info", "--output=json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    if info.get("format") != "qcow2":
        raise SystemExit(f"{path}: expected qcow2, got {info.get('format')!r}")
    if info.get("virtual-size") != expected_size:
        raise SystemExit(
            f"{path}: expected virtual size {expected_size}, got {info.get('virtual-size')}"
        )
print("Validated retained partial-run qcow2 disks.")
PY
else
  qemu-img convert -p -O qcow2 "$BASE_IMAGE" "$OS_DISK"
  qemu-img resize "$OS_DISK" "$OS_SIZE"
  qemu-img create -f qcow2 "$QUAL_DISK" "$QUAL_SIZE"
fi

# Ensure the runtime QEMU identity can open the retained/new qcow2 disks read-write.
sudo setfacl -m "u:${QEMU_RUNTIME_USER}:rw-" "$OS_DISK" "$QUAL_DISK"
for disk in "$OS_DISK" "$QUAL_DISK"; do
  if ! sudo -u "$QEMU_RUNTIME_USER" test -r "$disk" || ! sudo -u "$QEMU_RUNTIME_USER" test -w "$disk"; then
    echo "ERROR: QEMU runtime account lacks read/write access to $disk" >&2
    namei -l "$disk" >&2 || true
    getfacl -p "$disk" >&2 || true
    exit 2
  fi
done

virt_args=(
  --connect qemu:///system
  --name "$VM_NAME"
  --memory "$MEM_MIB"
  --vcpus "${VCPUS},cpuset=${CPUSET},sockets=1,cores=${VCPUS},threads=1"
  --numatune "${NUMA_NODE},memory.mode=strict"
  --cpu host-passthrough
  --machine q35
  --boot uefi
  --tpm backend.type=emulator,backend.version=2.0,model=tpm-crb
  --disk "path=${OS_DISK},format=qcow2,bus=virtio,cache=none,io=native"
  --disk "path=${QUAL_DISK},format=qcow2,bus=virtio,cache=none,io=native"
  --network network=edgew-vt-mgmt,model=virtio
  --network network=edgew-vt-source,model=virtio
  --network network=edgew-vt-upstream,model=virtio
  --network network=edgew-vt-fault,model=virtio
  --osinfo detect=on,name=ubuntu24.04
  --import
  --cloud-init "clouduser-ssh-key=${SSH_KEY},disable=on"
  --graphics none
  --console pty,target.type=serial
  --noautoconsole
)

PRECHECK_XML="${VM_DIR}/virt-install-preflight.xml"
PRECHECK_ERR="${VM_DIR}/virt-install-preflight.err"
INSTALL_LOG="${VM_DIR}/virt-install.log"

echo "Running virt-install configuration preflight..."
if ! virt-install "${virt_args[@]}" --dry-run --print-xml >"$PRECHECK_XML" 2>"$PRECHECK_ERR"; then
  echo "ERROR: virt-install preflight failed before domain creation." >&2
  echo "Diagnostic: $PRECHECK_ERR" >&2
  cat "$PRECHECK_ERR" >&2
  exit 2
fi

echo "virt-install preflight passed; retained XML: $PRECHECK_XML"
echo "Defining and starting VT0; diagnostic log: $INSTALL_LOG"
if ! virt-install --debug "${virt_args[@]}" > >(tee "$INSTALL_LOG") 2>&1; then
  echo "ERROR: virt-install failed. No overwrite/retry was attempted." >&2
  echo "Retained diagnostic log: $INSTALL_LOG" >&2
  exit 2
fi

virsh --connect qemu:///system autostart "$VM_NAME"

echo
virsh --connect qemu:///system dominfo "$VM_NAME"
virsh --connect qemu:///system domiflist "$VM_NAME"
echo
printf 'VT0 DUT created.\n'
printf 'SSH private key: %s\n' "${SSH_KEY%.pub}"
printf 'Discover the management lease with: virsh net-dhcp-leases edgew-vt-mgmt\n'
printf 'Do not interpret this VM as physical EDGE-RT0 qualification evidence.\n'
