"""Collect build-environment metadata and installed license evidence, not an SBOM."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def collect(output: Path, distributions: Iterable[Any] | None = None) -> dict[str, Any]:
    if output.exists():
        raise ValueError('Choose a fresh evidence directory')
    output.mkdir(parents=True)
    records = []
    installed = list(metadata.distributions() if distributions is None else distributions)
    installed.sort(key=lambda dist: (dist.metadata.get('Name', '').lower(), dist.version))
    for index, dist in enumerate(installed):
        name = dist.metadata.get('Name', 'unknown')
        slug = re.sub(r'[^A-Za-z0-9_.-]', '_', name)[:100]
        directory = output / f'{index:04d}-{slug}'
        files = []
        for candidate in sorted(dist.files or [], key=str):
            # Metadata records evidence installed by the distribution; never traverse
            # arbitrary metadata paths outside its installation root.
            relative = Path(str(candidate))
            if relative.is_absolute() or '..' in relative.parts:
                continue
            if not any(re.match(r'^(licenses?|licences?|copying|notices?)([._-]|$)', part, re.I)
                       for part in relative.parts):
                continue
            source = Path(dist.locate_file(candidate))
            root = Path(dist.locate_file('')).resolve()
            if (source.is_symlink() or not source.is_file()
                    or not source.resolve().is_relative_to(root)):
                continue
            content = source.read_bytes()
            directory.mkdir(exist_ok=True)
            # Flatten to generated filenames; retain original relative path in manifest.
            destination = directory / f'{len(files):04d}-{source.name}'
            destination.write_bytes(content)
            files.append({'installedPath': str(candidate),
                          'evidencePath': destination.relative_to(output).as_posix(),
                          'sha256': hashlib.sha256(content).hexdigest()})
        records.append({
            'name': name, 'version': dist.version,
            'licenseExpression': dist.metadata.get('License-Expression'),
            'licenseMetadata': dist.metadata.get('License'),
            'licenseClassifiers': [value for value in dist.metadata.get_all('Classifier', [])
                                   if value.startswith('License ::')],
            'requiresDist': dist.metadata.get_all('Requires-Dist', []),
            'licenseFiles': files,
            'reviewStatus': 'unreviewed',
            'missingLicenseFiles': not bool(files),
        })
    result = {
        'schemaVersion': 1,
        'scope': 'installed Python build environment; includes build/test tools',
        'completeRuntimeSbom': False,
        'redistributionApproved': False,
        'pythonVersion': platform.python_version(),
        'platform': platform.platform(),
        'limitations': [
            'Not an exact inventory of frozen modules or native binaries.',
            'Python, WebView2 and native binary notices need separate review.',
            'License metadata and copied files do not establish redistribution permission.',
        ],
        'distributions': records,
    }
    (output / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    collect(args.output)
