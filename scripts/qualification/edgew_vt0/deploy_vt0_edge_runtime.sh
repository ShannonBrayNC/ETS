#!/usr/bin/env bash
set -euo pipefail

VM_HOST="192.168.250.10"
VM_USER="etsadmin"
SSH_KEY="${HOME}/.ssh/edgew_vt0"
QUAL_MOUNT="/var/lib/ets-qualification"
APPLY=0

usage() {
  cat <<'EOF'
Usage:
  deploy_vt0_edge_runtime.sh [--host IP] [--user USER] [--ssh-key PATH] [--apply]

Plan-only by default. --apply is required before package installation, Docker
configuration, source transfer, image build, or service startup.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) VM_HOST="${2:?missing value for --host}"; shift 2 ;;
    --user) VM_USER="${2:?missing value for --user}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?missing value for --ssh-key}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for cmd in git ssh scp sha256sum gzip mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required host command missing: $cmd" >&2
    exit 2
  }
done

[[ -r "$SSH_KEY" ]] || {
  echo "ERROR: SSH private key not readable: $SSH_KEY" >&2
  exit 2
}

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "ERROR: run from the ETS repository." >&2
  exit 2
}

SOURCE_SHA="$(git rev-parse HEAD)"
SOURCE_BRANCH="$(git branch --show-current)"
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: local repository has uncommitted changes; refusing to package an ambiguous build." >&2
  exit 2
fi

SSH=(
  ssh
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=5
  -i "$SSH_KEY"
  "${VM_USER}@${VM_HOST}"
)

"${SSH[@]}" 'sudo -n true' || {
  echo "ERROR: guest SSH/sudo preflight failed." >&2
  exit 2
}

REMOTE_STATE="$("${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
findmnt -n -o SOURCE,FSTYPE,TARGET "$QUAL_MOUNT" || true
command -v docker || true
if [[ -f /etc/docker/daemon.json ]]; then
  echo "--- /etc/docker/daemon.json ---"
  sudo cat /etc/docker/daemon.json
fi
REMOTE
)"

cat <<EOF
EDGEW-RT0-VT0 Edge runtime deployment plan
  source branch:       $SOURCE_BRANCH
  source commit:       $SOURCE_SHA
  guest:               ${VM_USER}@${VM_HOST}
  qualification mount: $QUAL_MOUNT
  docker data-root:    $QUAL_MOUNT/docker
  release root:        /opt/ets/releases/$SOURCE_SHA
  compose file:        /opt/ets/current/edge-demo/docker-compose.yml

Current guest state:
$REMOTE_STATE

Actions on --apply:
  1. Verify $QUAL_MOUNT is backed by /dev/vdb1 and labeled ETS_QUAL.
  2. Install docker.io and docker-compose-v2 if required.
  3. Configure Docker data-root under the dedicated qualification volume.
  4. Transfer an exact git archive of commit $SOURCE_SHA.
  5. Retain archive/configuration hashes without copying credentials or private keys.
  6. Build and start the four-service Edge Virtual stack.
  7. Require /ready and public device identity endpoints to respond.

Claim boundary: simulated VT0 build/runtime preparation only; not physical EDGE-RT0 qualification.
EOF

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "PLAN ONLY: guest packages, Docker configuration, source, and services were not changed."
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/ets-$SOURCE_SHA.tar.gz"

git archive --format=tar "$SOURCE_SHA" | gzip -n >"$ARCHIVE"
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"

"${SSH[@]}" "bash -s" <<'REMOTE'
set -euo pipefail
QUAL_MOUNT=/var/lib/ets-qualification

source_line="$(findmnt -n -o SOURCE "$QUAL_MOUNT")"
fstype="$(findmnt -n -o FSTYPE "$QUAL_MOUNT")"
label="$(sudo blkid -s LABEL -o value "$source_line")"

[[ "$source_line" == "/dev/vdb1" ]] || {
  echo "ERROR: qualification mount is not /dev/vdb1: $source_line" >&2
  exit 3
}
[[ "$fstype" == "ext4" ]] || {
  echo "ERROR: qualification filesystem is not ext4: $fstype" >&2
  exit 3
}
[[ "$label" == "ETS_QUAL" ]] || {
  echo "ERROR: qualification filesystem label is not ETS_QUAL: $label" >&2
  exit 3
}

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 ca-certificates curl jq

if [[ -s /etc/docker/daemon.json ]]; then
  current="$(sudo jq -r '."data-root" // empty' /etc/docker/daemon.json 2>/dev/null || true)"
  if [[ -n "$current" && "$current" != "/var/lib/ets-qualification/docker" ]]; then
    echo "ERROR: existing Docker data-root differs from qualification contract: $current" >&2
    exit 3
  fi
fi

sudo install -d -m 0750 -o root -g docker /var/lib/ets-qualification/docker
printf '%s
' '{"data-root":"/var/lib/ets-qualification/docker"}'   | sudo tee /etc/docker/daemon.json >/dev/null
sudo systemctl enable --now docker
sudo systemctl restart docker
sudo usermod -aG docker "$USER"

sudo install -d -m 0755 /opt/ets/releases
REMOTE

scp -q -i "$SSH_KEY" "$ARCHIVE" "${VM_USER}@${VM_HOST}:/tmp/ets-release.tar.gz"

"${SSH[@]}" "bash -s" -- "$SOURCE_SHA" "$ARCHIVE_SHA" <<'REMOTE'
set -euo pipefail
SOURCE_SHA="$1"
ARCHIVE_SHA="$2"
RELEASE="/opt/ets/releases/$SOURCE_SHA"
QUAL_MOUNT="/var/lib/ets-qualification"
EVIDENCE="$QUAL_MOUNT/deployment-evidence/$SOURCE_SHA"

actual="$(sha256sum /tmp/ets-release.tar.gz | awk '{print $1}')"
[[ "$actual" == "$ARCHIVE_SHA" ]] || {
  echo "ERROR: transferred archive digest mismatch." >&2
  exit 4
}

sudo rm -rf "$RELEASE"
sudo install -d -m 0755 "$RELEASE" "$EVIDENCE"
sudo tar -xzf /tmp/ets-release.tar.gz -C "$RELEASE"
printf '%s
' "$SOURCE_SHA" | sudo tee "$RELEASE/.ets-build-commit" >/dev/null
printf '%s
' "$ARCHIVE_SHA" | sudo tee "$RELEASE/.ets-source-archive-sha256" >/dev/null
sudo ln -sfn "$RELEASE" /opt/ets/current

{
  echo "source_commit=$SOURCE_SHA"
  echo "source_archive_sha256=$ARCHIVE_SHA"
  echo "captured_at=$(date -u --iso-8601=seconds)"
  echo "docker=$(docker --version)"
  echo "compose=$(docker compose version)"
  sha256sum     "$RELEASE/edge-demo/docker-compose.yml"     "$RELEASE/edge-demo/Dockerfile.api"     "$RELEASE/edge-demo/Dockerfile.webhook"     "$RELEASE/edge-demo/Dockerfile.upstream"     "$RELEASE/edge-demo/Dockerfile.ui"
} | sudo tee "$EVIDENCE/build-provenance.txt" >/dev/null

cd /opt/ets/current
sudo docker compose -f edge-demo/docker-compose.yml build   2>&1 | sudo tee "$EVIDENCE/docker-build.log"
sudo docker compose -f edge-demo/docker-compose.yml up -d   2>&1 | sudo tee "$EVIDENCE/docker-up.log"

for _ in {1..60}; do
  if curl -fsS http://127.0.0.1:8400/ready >"$EVIDENCE/ready.json" 2>/dev/null; then
    break
  fi
  sleep 2
done

curl -fsS http://127.0.0.1:8400/ready >"$EVIDENCE/ready.json"
curl -fsS http://127.0.0.1:8400/version >"$EVIDENCE/version.json"
curl -fsS http://127.0.0.1:8400/edge/v1/device/identity >"$EVIDENCE/device-identity.json"
sudo docker compose -f edge-demo/docker-compose.yml ps --format json >"$EVIDENCE/compose-ps.jsonl"
sudo docker image inspect   "$(sudo docker compose -f edge-demo/docker-compose.yml images -q | sort -u)"   >"$EVIDENCE/image-inspect.json" 2>/dev/null || true

(
  cd "$EVIDENCE"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P
'     | sort | xargs -r sha256sum > SHA256SUMS
)

echo "Edge runtime deployed from exact commit: $SOURCE_SHA"
echo "Deployment evidence: $EVIDENCE"
echo "Public identity:"
cat "$EVIDENCE/device-identity.json"
REMOTE

echo
echo "VT0 Edge runtime deployment complete."
echo "Installed source commit: $SOURCE_SHA"
echo "No API key or signing private-key bytes were copied to host evidence."
