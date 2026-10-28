import hashlib
import importlib.util
import json
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    'dependency_evidence',
    Path(__file__).parents[2] / 'packaging/windows/collect_dependency_evidence.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def distribution(root, name='example', files=()):
    meta = Message()
    meta['Name'] = name
    meta['License-Expression'] = 'MIT'
    meta['Classifier'] = 'License :: OSI Approved :: MIT License'
    meta['Requires-Dist'] = 'dependency>=1'
    return SimpleNamespace(metadata=meta, version='1.2.3', files=files,
                           locate_file=lambda path: root / str(path))


def test_copies_license_bytes_and_records_missing_evidence(tmp_path):
    installed = tmp_path / 'installed'
    license_file = installed / 'example.dist-info/licenses/LICENSE.txt'
    license_file.parent.mkdir(parents=True)
    license_file.write_bytes(b'license\r\nnotice\xff')
    output = tmp_path / 'evidence'
    result = module.collect(output, [distribution(installed, files=[
        'example.dist-info/licenses/LICENSE.txt']), distribution(installed, name='missing')])
    first, missing = result['distributions']
    evidence = first['licenseFiles'][0]
    assert (output / evidence['evidencePath']).read_bytes() == license_file.read_bytes()
    assert evidence['sha256'] == hashlib.sha256(license_file.read_bytes()).hexdigest()
    assert first['licenseExpression'] == 'MIT'
    assert first['requiresDist'] == ['dependency>=1']
    assert missing['missingLicenseFiles'] is True
    assert result['redistributionApproved'] is False
    assert result['completeRuntimeSbom'] is False
    assert json.loads((output / 'inventory.json').read_text()) == result


def test_rejects_existing_output_without_changing_it(tmp_path):
    marker = tmp_path / 'keep'
    marker.write_text('preserve')
    with pytest.raises(ValueError, match='fresh'):
        module.collect(tmp_path, [])
    assert marker.read_text() == 'preserve'


def test_ignores_escape_paths_and_sanitizes_distribution_name(tmp_path):
    root = tmp_path / 'installed'
    root.mkdir()
    (tmp_path / 'LICENSE').write_text('outside')
    (root / 'LICENSE').write_text('inside')
    output = tmp_path / 'evidence'
    result = module.collect(output, [distribution(root, name='../bad/name', files=[
        '../LICENSE', str(tmp_path / 'LICENSE'), 'LICENSE'])])
    files = result['distributions'][0]['licenseFiles']
    assert len(files) == 1
    assert (output / files[0]['evidencePath']).resolve().is_relative_to(output)
    assert (output / files[0]['evidencePath']).read_text() == 'inside'


def test_ignores_symlink_outside_installation(tmp_path):
    root = tmp_path / 'installed'
    root.mkdir()
    (tmp_path / 'LICENSE').write_text('outside')
    try:
        (root / 'LICENSE').symlink_to(tmp_path / 'LICENSE')
    except OSError:
        pytest.skip('symlinks unavailable')
    result = module.collect(tmp_path / 'evidence', [distribution(root, files=['LICENSE'])])
    assert result['distributions'][0]['licenseFiles'] == []
