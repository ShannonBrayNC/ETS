from pathlib import Path

import pytest

from ets.desktop import host
from ets.desktop.smoke import NativeSmoke


def test_smoke_uses_copied_fixture_and_private_report(tmp_path):
    source = tmp_path / 'original.json'
    source.write_bytes(b'{"original": true}')
    temporary = tmp_path / 'temporary'
    temporary.mkdir()
    scenario = NativeSmoke(source, temporary)
    assert Path(scenario.choose('bundle')).read_bytes() == source.read_bytes()
    scenario.bundle.write_text('{')
    assert source.read_bytes() == b'{"original": true}'
    assert Path(scenario.choose('json')).parent == temporary
    assert scenario.choose('trust') is None


def test_smoke_fixture_requires_explicit_smoke_mode(monkeypatch):
    monkeypatch.setattr('sys.argv', ['ets-desktop', '--smoke-bundle', 'unused.json'])
    monkeypatch.setattr(host, '_launch', lambda *args: pytest.fail('must not launch'))
    with pytest.raises(SystemExit) as exc:
        host.main()
    assert exc.value.code == 2
