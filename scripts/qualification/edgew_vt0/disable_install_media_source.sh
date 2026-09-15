#!/usr/bin/env bash
set -euo pipefail

# Disable only active APT installer-media sources (cdrom:/ or file:/cdrom).
# Creates .pre-ets backups before changing any source file.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as the normal operator account; this script uses sudo explicitly." >&2
  exit 2
fi

sudo python3 - <<'PY'
from pathlib import Path
import re

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
    if 'cdrom:' not in original and 'file:/cdrom' not in original:
        continue

    backup = Path(str(path) + '.pre-ets')
    if not backup.exists():
        backup.write_text(original)

    if path.suffix == '.sources':
        stanzas = re.split(r'\n\s*\n', original.strip())
        out = []
        modified = False
        for stanza in stanzas:
            if ('cdrom:' in stanza or 'file:/cdrom' in stanza):
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
            active_media = (
                ('cdrom:' in line or 'file:/cdrom' in line)
                and not stripped.startswith('#')
            )
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
if sudo grep -RnsE '^[[:space:]]*deb .*?(cdrom:|file:/cdrom)|^[[:space:]]*URIs:[[:space:]]*(cdrom:|file:/cdrom)' \
  /etc/apt/sources.list /etc/apt/sources.list.d --include='*.list' --include='*.sources' 2>/dev/null; then
  echo "NOTE: matching text remains above; .sources entries with 'Enabled: no' are expected and disabled." >&2
fi

sudo apt-get update
printf '\nAPT update succeeded without an active installer-media repository.\n'
