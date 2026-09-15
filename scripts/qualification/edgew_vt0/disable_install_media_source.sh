#!/usr/bin/env bash
set -euo pipefail

# Disable only active APT installer-media sources (cdrom:/ or file:/.../cdrom).
# Creates .pre-ets backups before changing any source file.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as the normal operator account; this script uses sudo explicitly." >&2
  exit 2
fi

sudo python3 - <<'PY'
from pathlib import Path
import re

MEDIA_RE = re.compile(r'(?i)(?:cdrom:|file:/+cdrom(?:/|\b))')

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
    if not MEDIA_RE.search(original):
        continue

    backup = Path(str(path) + '.pre-ets')
    if not backup.exists():
        backup.write_text(original)

    if path.suffix == '.sources':
        stanzas = re.split(r'\n\s*\n', original.strip())
        out = []
        modified = False
        for stanza in stanzas:
            if MEDIA_RE.search(stanza):
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
            active_media = MEDIA_RE.search(line) and not stripped.startswith('#')
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

printf '\nRemaining CD-ROM references under active APT source files:\n'
sudo grep -RnsEi 'cdrom:|file:/+cdrom' \
  /etc/apt/sources.list /etc/apt/sources.list.d \
  --include='*.list' --include='*.sources' 2>/dev/null || true

printf '\nVerifying active APT sources...\n'
sudo apt-get update
printf '\nAPT update succeeded without an active installer-media repository.\n'
