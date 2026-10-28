import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'candidate_record', Path(__file__).parents[2] / 'packaging/windows/candidate_record.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def candidate(tmp_path):
    packages, results, output = [tmp_path / name for name in ('packages', 'results', 'review')]
    packages.mkdir()
    results.mkdir()
    (packages / 'candidate.msix').write_bytes(b'unsigned test package')
    (packages / 'qualification.json').write_text(json.dumps({
        'package': 'candidate.msix', 'sha256': module.digest(packages / 'candidate.msix'),
        'signed': False, 'manifestValidated': True, 'payloadHashesVerified': True}))
    (packages / 'layout').mkdir()
    (packages / 'layout/ignore.txt').write_text('working tree')
    (results / 'smoke.json').write_text('{"status":0}')
    return packages, results, output


def build(candidate):
    return module.assemble(*candidate, 'a' * 40,
                           'https://github.com/ShannonBrayNC/ETS/actions/runs/123')


def test_self_contained_inventory(candidate):
    record = build(candidate)
    assert len(record['files']) == 3
    assert module.verify(candidate[2]) == record
    assert record['releaseApproved'] is False
    assert record['recordSigned'] is False
    assert not (candidate[2] / 'package/layout').exists()


@pytest.mark.parametrize('change', ['tamper', 'missing', 'extra'])
def test_detects_evidence_changes(candidate, change):
    build(candidate)
    output = candidate[2]
    path = output / 'results/smoke.json'
    if change == 'tamper':
        path.write_text('{"status":1}')
    elif change == 'missing':
        path.unlink()
    else:
        (output / 'extra').write_text('unexpected')
    with pytest.raises(ValueError):
        module.verify(output)


def test_rejects_traversal_record(candidate):
    record = build(candidate)
    record['files']['../outside'] = {'bytes': 1, 'sha256': '0' * 64}
    (candidate[2] / 'candidate.json').write_text(json.dumps(record))
    with pytest.raises(ValueError, match='Unsafe'):
        module.verify(candidate[2])


def test_refuses_existing_output(candidate):
    build(candidate)
    before = (candidate[2] / 'candidate.json').read_bytes()
    with pytest.raises(ValueError, match='fresh'):
        build(candidate)
    assert (candidate[2] / 'candidate.json').read_bytes() == before


def test_refuses_mismatched_package_hash(candidate):
    (candidate[0] / 'candidate.msix').write_text('changed')
    with pytest.raises(ValueError, match='qualification'):
        build(candidate)
    assert not candidate[2].exists()


def test_refuses_output_inside_input(candidate):
    with pytest.raises(ValueError, match='outside'):
        build((candidate[0], candidate[1], candidate[1] / 'review'))


def test_refuses_symlink_evidence(candidate):
    link = candidate[1] / 'linked.json'
    try:
        link.symlink_to(candidate[1] / 'smoke.json')
    except OSError:
        pytest.skip('symlinks unavailable')
    with pytest.raises(ValueError, match='symlinks'):
        build(candidate)
    assert not candidate[2].exists()


@pytest.mark.parametrize('field,value', [
    ('schemaVersion', True), ('sourceSha', 'not-a-commit'),
    ('workflowRun', 'https://example.com/run'), ('recordSigned', True),
    ('releaseApproved', True), ('files', []),
])
def test_rejects_invalid_record_metadata(candidate, field, value):
    record = build(candidate)
    record[field] = value
    (candidate[2] / 'candidate.json').write_text(json.dumps(record))
    with pytest.raises(ValueError):
        module.verify(candidate[2])


@pytest.mark.parametrize('entry', [None, [], {'bytes': True, 'sha256': '0' * 64},
                                    {'bytes': -1, 'sha256': '0' * 64},
                                    {'bytes': 12, 'sha256': 'bad'}])
def test_rejects_invalid_file_record(candidate, entry):
    record = build(candidate)
    record['files']['results/smoke.json'] = entry
    (candidate[2] / 'candidate.json').write_text(json.dumps(record))
    with pytest.raises(ValueError):
        module.verify(candidate[2])


def test_rejects_duplicate_json_fields(candidate):
    build(candidate)
    manifest = candidate[2] / 'candidate.json'
    manifest.write_text(manifest.read_text().replace('"schemaVersion": 1',
                                                   '"schemaVersion": 2, "schemaVersion": 1'))
    with pytest.raises(ValueError, match='Duplicate'):
        module.verify(candidate[2])


def test_rejects_non_object_record(candidate):
    build(candidate)
    (candidate[2] / 'candidate.json').write_text('[]')
    with pytest.raises(ValueError):
        module.verify(candidate[2])


def test_rejects_windows_junction(candidate, tmp_path):
    import subprocess
    import sys

    if sys.platform != 'win32':
        pytest.skip('Windows directory junction regression')
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'private.txt').write_text('must not copy')
    junction = candidate[1] / 'junction'
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)],
                   check=True, capture_output=True)
    try:
        with pytest.raises(ValueError, match='reparse|symlink'):
            build(candidate)
        assert not candidate[2].exists()
    finally:
        junction.rmdir()
