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
echo "--- filesystems ---"
df -h / "$QUAL_MOUNT" || true
echo "--- docker/containerd commands ---"
command -v docker || true
command -v containerd || true
if [[ -f /etc/docker/daemon.json ]]; then
  echo "--- /etc/docker/daemon.json ---"
  sudo cat /etc/docker/daemon.json
fi
if [[ -f /etc/containerd/config.toml ]]; then
  echo "--- containerd root/state ---"
  sudo grep -E '^(root|state)[[:space:]]*=' /etc/containerd/config.toml || true
fi
if [[ -d /var/lib/containerd ]]; then
  echo "--- legacy containerd root usage ---"
  sudo du -sh /var/lib/containerd 2>/dev/null || true
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
  3. Configure Docker data-root and containerd content root under the dedicated qualification volume.
  4. Remove only stale/incomplete containerd cache from the guest root filesystem after both daemons are stopped.
  5. Transfer an exact git archive of commit $SOURCE_SHA.
  6. Retain archive/configuration hashes without copying credentials or private keys.
  7. Build and start the four-service Edge Virtual stack.
  8. Require /ready and public device identity endpoints to respond.

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

# A failed BuildKit/containerd pull can fill the 64 GiB OS disk even when
# Docker's data-root is redirected. Re-home containerd separately before retry.
if ! command -v docker >/dev/null 2>&1 || ! command -v containerd >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker.io docker-compose-v2 containerd ca-certificates curl jq
fi

sudo systemctl stop docker.service docker.socket 2>/dev/null || true
sudo systemctl stop containerd.service 2>/dev/null || true

sudo install -d -m 0750 -o root -g docker /var/lib/ets-qualification/docker
sudo install -d -m 0711 -o root -g root /var/lib/ets-qualification/containerd

# Free the 64 GiB guest root before writing daemon configuration. This path
# contains only disposable containerd cache/content on the isolated VT0 guest.
if [[ -d /var/lib/containerd && ! -L /var/lib/containerd ]]; then
  sudo install -d -m 0755 /var/lib/ets-qualification/runtime-recovery
  {
    echo "captured_at=$(date -u --iso-8601=seconds)"
    sudo du -sh /var/lib/containerd 2>/dev/null || true
    sudo find /var/lib/containerd -maxdepth 2 -mindepth 1 -printf '%p %s\n' 2>/dev/null | head -5000 || true
  } | sudo tee /var/lib/ets-qualification/runtime-recovery/legacy-containerd-root.txt >/dev/null
  sudo rm -rf /var/lib/containerd/*
fi
sudo apt-get clean || true

if [[ -s /etc/docker/daemon.json ]]; then
  current="$(sudo jq -r '."data-root" // empty' /etc/docker/daemon.json 2>/dev/null || true)"
  if [[ -n "$current" && "$current" != "/var/lib/ets-qualification/docker" ]]; then
    echo "ERROR: existing Docker data-root differs from qualification contract: $current" >&2
    exit 3
  fi
fi
printf '%s
' '{"data-root":"/var/lib/ets-qualification/docker"}' \
  | sudo tee /etc/docker/daemon.json >/dev/null

if [[ -f /etc/containerd/config.toml ]]; then
  sudo cp -a /etc/containerd/config.toml /etc/containerd/config.toml.pre-ets-vt0
else
  sudo containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
fi

if sudo grep -qE '^root[[:space:]]*=' /etc/containerd/config.toml; then
  sudo sed -i -E \
    '0,/^root[[:space:]]*=/{s#^root[[:space:]]*=.*#root = "/var/lib/ets-qualification/containerd"#}' \
    /etc/containerd/config.toml
else
  printf '%s
' 'root = "/var/lib/ets-qualification/containerd"' \
    | sudo tee -a /etc/containerd/config.toml >/dev/null
fi

sudo systemctl enable --now containerd.service
sudo systemctl enable --now docker.service
sudo usermod -aG docker "$USER"

docker_root="$(sudo docker info --format '{{.DockerRootDir}}')"
containerd_root="$(sudo awk -F'= *' '/^root[[:space:]]*=/{gsub(/"/,"",$2); print $2; exit}' /etc/containerd/config.toml)"

[[ "$docker_root" == "/var/lib/ets-qualification/docker" ]] || {
  echo "ERROR: Docker root is not on qualification storage: $docker_root" >&2
  exit 3
}
[[ "$containerd_root" == "/var/lib/ets-qualification/containerd" ]] || {
  echo "ERROR: containerd root is not on qualification storage: $containerd_root" >&2
  exit 3
}

avail_bytes="$(df -B1 --output=avail "$QUAL_MOUNT" | tail -1 | tr -d ' ')"
[[ "$avail_bytes" -ge $((100 * 1024 * 1024 * 1024)) ]] || {
  echo "ERROR: less than 100 GiB free on qualification storage." >&2
  exit 3
}

echo "Runtime storage placement verified:"
echo "  DockerRootDir=$docker_root"
echo "  containerd_root=$containerd_root"
df -h / "$QUAL_MOUNT"

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
  echo "docker_root=$(sudo docker info --format '{{.DockerRootDir}}')"
  echo "containerd_root=$(sudo awk -F'= *' '/^root[[:space:]]*=/{gsub(/"/,"",$2); print $2; exit}' /etc/containerd/config.toml)"
  df -h / "$QUAL_MOUNT"
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
