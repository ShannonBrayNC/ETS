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


def test_signed_fixture_is_valid_and_tampering_fails(tmp_path):
    from ets.desktop.controller import DesktopAPI

    fixtures = Path(__file__).parents[1] / 'fixtures/verifier'
    fixture = fixtures / 'native-signed.json'
    trust = fixtures / 'native-trust.json'
    original_bundle, original_trust = fixture.read_bytes(), trust.read_bytes()
    scenario = NativeSmoke(fixture, tmp_path, trust)
    api = DesktopAPI(scenario.choose)
    api.select_bundle()
    assert api.verify()['outcome']['status'] == 'indeterminate'
    api.select_trust()
    outcome = api.verify()['outcome']
    assert outcome['status'] == 'valid'
    assert outcome['signature_verified'] is True
    assert outcome['continuity_verified'] is False
    assert outcome['standing_status'] == 'checkpoint_only'
    import json

    payload = json.loads(scenario.bundle.read_bytes())
    payload['event']['metadata']['tampered'] = True
    scenario.bundle.write_text(json.dumps(payload))
    api.select_bundle()
    assert api.verify()['outcome']['status'] == 'invalid'
    scenario.trust.write_text('{}')
    assert fixture.read_bytes() == original_bundle
    assert trust.read_bytes() == original_trust


def test_smoke_trust_requires_bundle(monkeypatch):
    monkeypatch.setattr('sys.argv', ['ets-desktop', '--smoke-test', '--smoke-trust', 'unused'])
    monkeypatch.setattr(host, '_launch', lambda *args: pytest.fail('must not launch'))
    with pytest.raises(SystemExit) as exc:
        host.main()
    assert exc.value.code == 2
