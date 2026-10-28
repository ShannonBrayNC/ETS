"""Assemble and check an unsigned, self-contained engineering review bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import Any, cast


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reject_link(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Evidence must not contain symlinks or Windows reparse points')


def files_under(root: Path) -> list[Path]:
    reject_link(root)
    if not root.is_dir():
        raise ValueError('Evidence root must be a real directory')
    paths = []

    def fail(error: OSError) -> None:
        raise error

    # Inspect directory entries before os.walk descends into them. In particular,
    # Windows junctions are reparse points but are not necessarily symlinks.
    for directory, directories, filenames in os.walk(root, followlinks=False, onerror=fail):
        for name in directories + filenames:
            path = Path(directory) / name
            reject_link(path)
            if name in filenames:
                if not stat.S_ISREG(path.lstat().st_mode):
                    raise ValueError('Evidence must contain only regular files')
                paths.append(path)
    return sorted(paths)


def read_object(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError('Non-finite JSON value: ' + value)

    with path.open('rb') as stream:
        raw = stream.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Candidate metadata exceeds size limit')
    try:
        record = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                            parse_constant=invalid_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Malformed candidate metadata') from exc
    if not isinstance(record, dict):
        raise ValueError('Candidate metadata must be an object')
    return cast(dict[str, Any], record)


def valid_source(source: Any, url: Any) -> bool:
    return (isinstance(source, str) and re.fullmatch(r'[0-9a-f]{40}', source) is not None
            and isinstance(url, str) and re.fullmatch(
                r'https://github.com/ShannonBrayNC/ETS/actions/runs/[0-9]+', url) is not None)


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
    qualification = read_object(packages / 'qualification.json')
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
    record = read_object(manifest)
    if (type(record.get('schemaVersion')) is not int or record['schemaVersion'] != 1
            or not isinstance(record.get('files'), dict)
            or not valid_source(record.get('sourceSha'), record.get('workflowRun'))
            or record.get('recordSigned') is not False
            or record.get('releaseApproved') is not False):
        raise ValueError('Unsupported or invalid unsigned candidate record')
    expected = record['files']
    if not expected:
        raise ValueError('Empty candidate record')
    for relative, entry in expected.items():
        if (not isinstance(entry, dict) or type(entry.get('bytes')) is not int
                or entry['bytes'] < 0 or not isinstance(entry.get('sha256'), str)
                or re.fullmatch(r'[0-9a-f]{64}', entry['sha256']) is None):
            raise ValueError('Invalid candidate file record')
        path = PurePosixPath(relative)
        if (path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative
                or str(path) != relative or relative == 'candidate.json'):
            raise ValueError('Unsafe candidate path')
        target = root / relative
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError('Candidate path escapes review directory')
        if not target.is_file() or target.stat().st_size != entry['bytes']:
            raise ValueError('Missing or changed candidate file: ' + relative)
        if digest(target) != entry['sha256']:
            raise ValueError('Candidate hash mismatch: ' + relative)
    actual = {p.relative_to(root).as_posix() for p in paths} - {'candidate.json'}
    if actual != set(expected):
        raise ValueError('Unexpected files in candidate directory')
    return record


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
