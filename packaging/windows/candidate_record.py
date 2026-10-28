"""Assemble and check an unsigned, self-contained engineering review bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, cast


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files_under(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Evidence root must be a real directory')
    paths = sorted(root.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Evidence must not contain symlinks')
    return [path for path in paths if path.is_file()]


def assemble(packages: Path, results: Path, output: Path, source_sha: str,
             run_url: str) -> dict[str, Any]:
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('Expected an exact lowercase Git commit SHA')
    if not re.fullmatch(r'https://github.com/ShannonBrayNC/ETS/actions/runs/[0-9]+', run_url):
        raise ValueError('Expected an ETS GitHub Actions run URL')
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a fresh review directory')
    for root in (packages, results):
        if output.resolve().is_relative_to(root.resolve()):
            raise ValueError('Review directory must be outside evidence roots')
    package_files = files_under(packages)
    # Exclude local MakeAppx layout/unpacked working trees.
    selected = [p for p in package_files if p.parent == packages and
                p.suffix.lower() in {'.msix', '.json'}]
    msix = [p for p in selected if p.suffix.lower() == '.msix']
    if len(msix) != 1:
        raise ValueError('Expected exactly one MSIX candidate')
    qualification = json.loads((packages / 'qualification.json').read_text(encoding='utf-8-sig'))
    if (qualification.get('package') != msix[0].name
            or qualification.get('sha256') != digest(msix[0])
            or qualification.get('signed') is not False
            or qualification.get('manifestValidated') is not True
            or qualification.get('payloadHashesVerified') is not True):
        raise ValueError('Package qualification does not match the unsigned validated candidate')
    result_files = files_under(results)
    if not result_files:
        raise ValueError('Qualification results are missing')
    output.mkdir(parents=True)
    inventory = {}
    for prefix, root, selected_files in [('package', packages, selected),
                                          ('results', results, result_files)]:
        for source in selected_files:
            relative = PurePosixPath(prefix) / source.relative_to(root).as_posix()
            target = output / str(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            inventory[str(relative)] = {'sha256': digest(target), 'bytes': target.stat().st_size}
    record = {'schemaVersion': 1, 'sourceSha': source_sha, 'workflowRun': run_url,
              'recordSigned': False, 'releaseApproved': False,
              'scope': 'Engineering candidate and this Windows job evidence only',
              'limitations': ['Unsigned hashes do not authenticate origin.',
                              'Other CI jobs and client/Store approvals need separate evidence.'],
              'files': inventory}
    (output / 'candidate.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    if digest(output / 'package' / msix[0].name) != qualification['sha256']:
        raise ValueError('Package changed during assembly')
    verify(output)
    return record


def verify(root: Path) -> dict[str, Any]:
    paths = files_under(root)
    manifest = root / 'candidate.json'
    if manifest.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Candidate record exceeds size limit')
    record = json.loads(manifest.read_text(encoding='utf-8'))
    if record.get('schemaVersion') != 1 or not isinstance(record.get('files'), dict):
        raise ValueError('Unsupported candidate record')
    expected = record['files']
    if not expected:
        raise ValueError('Empty candidate record')
    for relative, entry in expected.items():
        path = PurePosixPath(relative)
        if (path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative
                or str(path) != relative or relative == 'candidate.json'):
            raise ValueError('Unsafe candidate path')
        target = root / relative
        if not target.is_file() or target.stat().st_size != entry['bytes']:
            raise ValueError('Missing or changed candidate file: ' + relative)
        if digest(target) != entry['sha256']:
            raise ValueError('Candidate hash mismatch: ' + relative)
    actual = {p.relative_to(root).as_posix() for p in paths} - {'candidate.json'}
    if actual != set(expected):
        raise ValueError('Unexpected files in candidate directory')
    return cast(dict[str, Any], record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('assemble')
    for name in ('packages', 'results', 'output'):
        build.add_argument('--' + name, type=Path, required=True)
    build.add_argument('--source-sha', required=True)
    build.add_argument('--run-url', required=True)
    check = commands.add_parser('verify')
    check.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.command == 'verify':
        verified = verify(args.directory)
        print(f"Verified {len(verified['files'])} file hashes; origin/release not approved.")
    else:
        assemble(args.packages, args.results, args.output, args.source_sha, args.run_url)
