from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qualify_hosted_azure_live.py"
_SPEC = importlib.util.spec_from_file_location("qualify_hosted_azure_live", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
qualification = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qualification)


def test_request_json_translates_read_timeout_to_retryable_runtime_error() -> None:
    with patch.object(qualification, "urlopen", side_effect=TimeoutError("read timed out")):
        with pytest.raises(RuntimeError, match="qualification endpoint was unreachable"):
            qualification._request_json("GET", "https://ets.internal/health")
