#!/usr/bin/env bash
set -euo pipefail

VM_HOST="192.168.250.10"
VM_USER="etsadmin"
SSH_KEY="${HOME}/.ssh/edgew_vt0"
VM_NAME="edgew-rt0-vt0-dut"
PHASE_A_ROOT="/srv/ets-lab/evidence/vt0-phase-a"

usage() {
  cat <<'EOF'
Usage:
  preflight_vt0_phase_b.sh [--host IP] [--user USER] [--ssh-key PATH]
                           [--vm NAME] [--phase-a-root PATH]

Read-only preflight for simulated VT0 Phase B:
  EDGE-HQP-DUR-001
  EDGE-HQP-BPR-001
  EDGE-HQP-OFF-001
  EDGE-HQP-CHK-001
  EDGE-HQP-OPS-001
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) VM_HOST="${2:?missing value for --host}"; shift 2 ;;
    --user) VM_USER="${2:?missing value for --user}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?missing value for --ssh-key}"; shift 2 ;;
    --vm) VM_NAME="${2:?missing value for --vm}"; shift 2 ;;
    --phase-a-root) PHASE_A_ROOT="${2:?missing value for --phase-a-root}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in ssh python3 find git; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required host command missing: $cmd" >&2
    exit 2
  }
done

[[ -r "$SSH_KEY" ]] || {
  echo "ERROR: SSH private key not readable: $SSH_KEY" >&2
  exit 2
}

LATEST_PHASE_A="$(
  find "$PHASE_A_ROOT" -mindepth 1 -maxdepth 1 -type d     -name "$VM_NAME-*" -printf '%T@ %p\n' 2>/dev/null   | sort -nr | head -1 | cut -d' ' -f2-
)"

[[ -n "$LATEST_PHASE_A" && -f "$LATEST_PHASE_A/phase-a-summary.json" ]] || {
  echo "ERROR: no retained Phase A summary found under $PHASE_A_ROOT" >&2
  exit 2
}

python3 - "$LATEST_PHASE_A/phase-a-summary.json" <<'PY'
import json
from pathlib import Path
import sys

summary = json.loads(Path(sys.argv[1]).read_text())
if summary.get("all_phase_a_cases_pass") is not True:
    raise SystemExit("ERROR: latest VT0 Phase A did not pass")
expected = {
    "EDGE-HQP-BLD-001",
    "EDGE-HQP-ID-001",
    "EDGE-HQP-SEC-001",
}
cases = summary.get("cases", {})
if not expected.issubset(cases):
    raise SystemExit("ERROR: Phase A summary is missing required case results")
print("Phase A dependency gate: PASS")
PY

SSH=(
  ssh
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=5
  -i "$SSH_KEY"
  "${VM_USER}@${VM_HOST}"
)

"${SSH[@]}" 'sudo -n true' >/dev/null || {
  echo "ERROR: guest SSH/sudo preflight failed." >&2
  exit 2
}

VERIFIER_PY=""
if [[ -x .venv/bin/python ]] && .venv/bin/python -c 'import ets.verifier.cli' >/dev/null 2>&1; then
  VERIFIER_PY=".venv/bin/python"
elif python3 -c 'import ets.verifier.cli' >/dev/null 2>&1; then
  VERIFIER_PY="python3"
fi

HOST_COMMIT="$(git rev-parse HEAD)"

echo
echo "=== HOST OBSERVER ==="
echo "host_commit=$HOST_COMMIT"
echo "phase_a_package=$LATEST_PHASE_A"
echo "verifier_python=${VERIFIER_PY:-UNAVAILABLE}"

echo
echo "=== DUT RUNTIME ==="
"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
BASE=/opt/ets/current/edge-demo/docker-compose.yml

echo "guest=$(hostname)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "dut_build=$(cat /opt/ets/current/.ets-build-commit)"
echo "qualification_mount=$(findmnt -n -o SOURCE,FSTYPE,TARGET /var/lib/ets-qualification)"
echo "docker_root=$(sudo docker info --format '{{.DockerRootDir}}')"
echo "containerd_root=$(sudo awk -F'= *' '/^root[[:space:]]*=/{gsub(/"/,"",$2); print $2; exit}' /etc/containerd/config.toml)"
echo "root_fs=$(df -hT / | tail -1)"
echo "qualification_fs=$(df -hT /var/lib/ets-qualification | tail -1)"
echo
echo "--- compose ---"
cd /opt/ets/current
sudo docker compose -f "$BASE" ps
echo
echo "--- readiness ---"
curl -fsS http://127.0.0.1:8400/ready
echo
echo
echo "--- public identity ---"
curl -fsS http://127.0.0.1:8400/edge/v1/device/identity
echo
echo
echo "--- protected queue status metadata ---"
API_KEY="$(
  sudo docker compose -f "$BASE" exec -T edge-api python -c     'from pathlib import Path; from ets.edge.device_identity import load_local_api_key; print(load_local_api_key(Path("/var/lib/ets/edge-local-api-key")))'
)"
CFG=$(mktemp)
trap 'rm -f "$CFG"' EXIT
printf 'header = "X-ETS-API-Key: %s"\n' "$API_KEY" >"$CFG"
chmod 600 "$CFG"
unset API_KEY
curl -q -K "$CFG" -fsS http://127.0.0.1:8400/edge/v1/sync/status
echo
REMOTE

echo
echo "=== PHASE B PLAN ==="
cat <<'EOF'
DUR-001
  Capture one synthetic webhook -> retain receipt/event/proof/bundle/tree head
  -> controlled edge-api restart -> re-read same event -> verify inclusion.

BPR-001
  Drain pending queue -> recreate only edge-webhook with temporary max_items=3
  -> stop only edge-upstream -> accept 3 synthetic records
  -> require 4th capture to fail explicitly with HTTP 503 backpressure
  -> reconnect/drain -> prove accepted records remain -> restore base config.

OFF-001
  Stop only edge-upstream -> capture synthetic record locally
  -> export and verify local proof -> run sync and observe retryable state
  -> restart edge-webhook -> prove queue persistence -> reconnect and drain.

CHK-001
  Retain the DUR pre-disruption checkpoint/inclusion proof
  -> after Phase B disruptions obtain later tree head
  -> verify consistency proof and re-verify the earlier inclusion proof.

OPS-001
  Export receipt/event/proof/bundle/tree head
  -> transfer public material to the T430 host
  -> run ETS Verifier there against a verifier-owned lab trust file
     derived from the retained public device identity.
EOF

echo
echo "=== RECOVERY / CLAIM BOUNDARY ==="
echo "- No Docker volumes will be deleted."
echo "- API key and private signing key bytes will not enter host evidence."
echo "- edge-upstream and base edge-webhook configuration must be restored after every run."
echo "- T430 verifier reproduction is independent execution, but not independent trust-anchor issuance."
echo "- All results remain claim_state=simulated; this is not physical EDGE-RT0 qualification."

if [[ -z "$VERIFIER_PY" ]]; then
  echo
  echo "BLOCKED: host ETS verifier runtime is unavailable; do not execute OPS-001 yet."
  exit 3
fi

echo
echo "PHASE_B_PREFLIGHT_READY=true"
