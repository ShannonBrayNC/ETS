from __future__ import annotations

from importlib import util
from pathlib import Path
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qualify_hosted_azure_live.py"
_SPEC = util.spec_from_file_location("qualify_hosted_azure_live", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
qualification = util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qualification)


def test_request_json_translates_read_timeout_to_retryable_runtime_error() -> None:
    with patch.object(qualification, "urlopen", side_effect=TimeoutError("read timed out")):
        try:
            qualification._request_json("GET", "https://ets.internal/health")
        except RuntimeError as exc:
            assert "qualification endpoint was unreachable" in str(exc)
        else:
            raise AssertionError("read timeout was not translated to a retryable RuntimeError")
