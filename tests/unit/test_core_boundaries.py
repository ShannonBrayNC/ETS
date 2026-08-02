"""Architecture and runtime boundary tests for the normative ETS Core."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tools.check_core_boundaries import DEFAULT_MANIFEST, validate

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_static_import_graph_and_public_api_manifest() -> None:
    graph = validate(DEFAULT_MANIFEST)
    assert "ets.core.api" in graph
    assert "ets.core.profiles" in graph["ets.core.api"]
    assert "ets.core.results" in graph["ets.core.api"]


def test_validator_cli_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "tools/check_core_boundaries.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "PASS"


def test_public_api_import_has_no_product_side_effects(tmp_path: Path) -> None:
    probe = r'''
import json
import logging
import os
import socket
import sqlite3
import sys
import threading
from pathlib import Path
violations = []
original_getenv = os.getenv
def guarded_getenv(key, *args, **kwargs):
    if key == "PYDANTIC_DISABLE_PLUGINS":
        return original_getenv(key, *args, **kwargs)
    violations.append(f"os.getenv:{key}")
    raise AssertionError(f"os.getenv:{key}")
def deny(name):
    def blocked(*args, **kwargs):
        violations.append(name)
        raise AssertionError(name)
    return blocked
os.getenv = guarded_getenv
socket.socket = deny("socket.socket")
socket.create_connection = deny("socket.create_connection")
sqlite3.connect = deny("sqlite3.connect")
logging.basicConfig = deny("logging.basicConfig")
threading.Thread.start = deny("thread.start")
before_files = sorted(str(path.relative_to(Path.cwd())) for path in Path.cwd().rglob("*"))
before_modules = set(sys.modules)
import ets.core.api as api
after_files = sorted(str(path.relative_to(Path.cwd())) for path in Path.cwd().rglob("*"))
forbidden_prefixes = (
    "azure", "boto3", "fastapi", "httpx", "redis", "requests", "sqlalchemy",
    "starlette", "uvicorn", "ets.api", "ets.cloud", "ets.edge", "ets.portal",
)
loaded = sorted(
    name for name in set(sys.modules) - before_modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
)
print(json.dumps({
    "files_unchanged": before_files == after_files,
    "loaded_forbidden": loaded,
    "violations": violations,
    "exports": list(api.__all__),
}, sort_keys=True))
'''
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPO_ROOT)
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["files_unchanged"] is True
    assert result["loaded_forbidden"] == []
    assert result["violations"] == []


def test_repeated_import_does_not_mutate_exports() -> None:
    probe = r'''
import importlib
import json
import ets.core.api as api
before = list(api.__all__)
identity = id(api)
reloaded = importlib.import_module("ets.core.api")
print(json.dumps({
    "same_module": id(reloaded) == identity,
    "same_exports": list(reloaded.__all__) == before,
}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == {"same_module": True, "same_exports": True}
