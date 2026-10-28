import re
from pathlib import Path

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from ets.desktop import host
from ets.edge import protected_ingress


@pytest.mark.parametrize('origin,expected', [
    ('http://localhost:8400', 201),
    ('http://localhost:8401', 403),
    ('http://attacker.example:8400', 403),
])
def test_local_proxy_preserves_port_for_capture(monkeypatch, origin, expected):
    monkeypatch.setenv('ETS_EDGE_UI_BFF_ENABLED', '1')
    monkeypatch.delenv('ETS_EDGE_UI_ALLOWED_ORIGIN', raising=False)
    config = Path('edge-demo/nginx.conf').read_text()
    block = config.split('location ^~ /edge/ui/v1/ {', 1)[1].split('}', 1)[0]
    variable = re.search(r'proxy_set_header Host (\$\w+);', block)[1]
    # Model the two nginx variables; exercise the real HTTP capture boundary.
    forwarded_host = {'$host': 'localhost', '$http_host': 'localhost:8400'}[variable]

    async def capture(_request):
        return JSONResponse({'event_id': 'local-test'}, status_code=201)

    monkeypatch.setattr(protected_ingress, '_ui_capture', capture)
    response = TestClient(protected_ingress.app).post(
        '/edge/ui/v1/capture', json={'payload': {'synthetic': True}},
        headers={'Host': forwarded_host, 'Origin': origin,
                 'Sec-Fetch-Site': 'same-origin', 'X-ETS-UI-Request': '1'},
    )
    assert response.status_code == expected


def test_startup_message_preserves_python_bridge_error():
    detail = 'Failed to resolve Python.Runtime.Loader.Initialize from C:\\ETS\\Python.Runtime.dll'
    message = host._startup_error_message(RuntimeError(detail))
    assert detail in message
    assert 'RuntimeError' in message
    assert 'blocked' in message
    assert 'Check that Microsoft Edge WebView2 Runtime is installed.' not in message


def test_startup_message_handles_unknown_error():
    message = host._startup_error_message(OSError('runtime unavailable'))
    assert 'OSError: runtime unavailable' in message
    assert 'WebView2' in message


def test_smoke_startup_failure_writes_actual_detail(monkeypatch, tmp_path):
    import json
    report = tmp_path / 'result.json'
    monkeypatch.setattr('sys.argv', ['ets-desktop', '--smoke-test', '--smoke-result', str(report)])
    def fail(*args):
        raise RuntimeError('Python bridge failed')
    monkeypatch.setattr(host, '_launch', fail)
    assert host.main() == 1
    assert json.loads(report.read_text()) == {'status': 1, 'detail': 'Python bridge failed'}
