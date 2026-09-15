#!/usr/bin/env bash
set -euo pipefail

printf 'ETS EDGEW-RT0-VT0 QEMU repository diagnostics\n'
printf 'OS: '
. /etc/os-release
printf '%s\n' "${PRETTY_NAME:-unknown}"
printf 'Architecture: %s\n\n' "$(dpkg --print-architecture)"

printf '== QEMU package policy ==\n'
apt-cache policy qemu-system-x86 qemu-system-x86-hwe qemu-system qemu-kvm || true

printf '\n== QEMU package visibility ==\n'
for pkg in qemu-system-x86 qemu-system-x86-hwe qemu-system qemu-kvm; do
  if apt-cache show "${pkg}" >/tmp/ets-qemu-show.$$ 2>/dev/null && [[ -s /tmp/ets-qemu-show.$$ ]]; then
    printf '%s: visible in APT cache\n' "${pkg}"
    sed -n '1,12p' /tmp/ets-qemu-show.$$
  else
    printf '%s: NOT visible in APT cache\n' "${pkg}"
  fi
  rm -f /tmp/ets-qemu-show.$$
  printf '\n'
done

printf '== Enabled APT binary indexes ==\n'
apt-get indextargets --format '$(SITE) $(RELEASE) $(COMPONENT) $(ARCHITECTURE) $(FILENAME)' 2>/dev/null \
  | grep -E '(^| )resolute([ -]|$)' \
  | sort -u || true

printf '\n== Deb822/list source definitions ==\n'
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do
  [[ -f "${f}" ]] || continue
  printf '\n--- %s ---\n' "${f}"
  grep -E '^(Types|URIs|Suites|Components|Architectures|Enabled):|^[[:space:]]*deb ' "${f}" || true
done

printf '\n== APT pinning/preferences mentioning QEMU or Ubuntu archives ==\n'
if compgen -G '/etc/apt/preferences' >/dev/null || compgen -G '/etc/apt/preferences.d/*' >/dev/null; then
  grep -RnsEi 'qemu|archive\.ubuntu|resolute' /etc/apt/preferences /etc/apt/preferences.d 2>/dev/null || true
else
  echo 'No APT preference files found.'
fi

printf '\n== Expected Ubuntu 26.04 package ==\n'
echo 'qemu-system-x86 is expected in Resolute main for amd64.'
echo 'If policy shows Candidate: (none), inspect whether a resolute/main amd64 Packages index is listed above.'
