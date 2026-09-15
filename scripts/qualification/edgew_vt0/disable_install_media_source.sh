#!/usr/bin/env bash
set -euo pipefail

# Disable only active APT installer-media sources (cdrom:/ or file:/+cdrom).
# Backups are stored outside sources.list.d so APT does not warn about them.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as the normal operator account; this script uses sudo explicitly." >&2
  exit 2
fi

BACKUP_DIR="/var/backups/ets-apt-sources"
sudo install -d -m 0755 "${BACKUP_DIR}"

# Move backups created by older versions of this script out of APT's source directory.
shopt -s nullglob
for legacy in /etc/apt/sources.list.d/*.pre-ets; do
  base="$(basename "${legacy}")"
  sudo mv "${legacy}" "${BACKUP_DIR}/${base}"
  echo "Moved legacy backup: ${legacy} -> ${BACKUP_DIR}/${base}"
done
shopt -u nullglob

sudo python3 - "${BACKUP_DIR}" <<'PY'
from pathlib import Path
import re
import shutil
import sys

backup_dir = Path(sys.argv[1])
media_re = re.compile(r'(?:cdrom:|file:/+cdrom)', re.IGNORECASE)

paths = []
main = Path('/etc/apt/sources.list')
if main.exists():
    paths.append(main)
source_dir = Path('/etc/apt/sources.list.d')
if source_dir.exists():
    paths.extend(sorted(source_dir.glob('*.list')))
    paths.extend(sorted(source_dir.glob('*.sources')))

changed = []
for path in paths:
    original = path.read_text(errors='replace')
    if not media_re.search(original):
        continue

    backup = backup_dir / (path.name + '.pre-ets')
    if not backup.exists():
        shutil.copy2(path, backup)

    if path.suffix == '.sources':
        stanzas = re.split(r'\n\s*\n', original.strip())
        out = []
        modified = False
        for stanza in stanzas:
            if media_re.search(stanza):
                if re.search(r'(?mi)^Enabled:\s*no\s*$', stanza):
                    out.append(stanza)
                    continue
                stanza = stanza.rstrip() + '\nEnabled: no'
                modified = True
            out.append(stanza)
        new = '\n\n'.join(out).rstrip() + '\n'
    else:
        out = []
        modified = False
        for line in original.splitlines():
            stripped = line.lstrip()
            active_media = media_re.search(line) and not stripped.startswith('#')
            if active_media:
                out.append('# ETS disabled install-media source: ' + line)
                modified = True
            else:
                out.append(line)
        new = '\n'.join(out) + '\n'

    if modified:
        path.write_text(new)
        changed.append(str(path))

if changed:
    print('Disabled installer-media APT source(s):')
    for path in changed:
        print('  ' + path)
else:
    print('No active installer-media APT source required modification.')
PY

printf '\nVerifying active APT sources...\n'
sudo python3 - <<'PY'
from pathlib import Path
import re
import sys

media_re = re.compile(r'(?:cdrom:|file:/+cdrom)', re.IGNORECASE)
paths = [Path('/etc/apt/sources.list')]
d = Path('/etc/apt/sources.list.d')
if d.exists():
    paths += sorted(d.glob('*.list')) + sorted(d.glob('*.sources'))

active = []
for path in paths:
    if not path.exists():
        continue
    text = path.read_text(errors='replace')
    if path.suffix == '.sources':
        for stanza in re.split(r'\n\s*\n', text):
            if media_re.search(stanza) and not re.search(r'(?mi)^Enabled:\s*no\s*$', stanza):
                active.append(str(path))
                break
    else:
        for line in text.splitlines():
            if not line.lstrip().startswith('#') and media_re.search(line):
                active.append(str(path))
                break

if active:
    print('ERROR: active installer-media source remains:', file=sys.stderr)
    for path in sorted(set(active)):
        print('  ' + path, file=sys.stderr)
    sys.exit(1)
PY

sudo apt-get update
printf '\nAPT update succeeded without an active installer-media repository.\n'
