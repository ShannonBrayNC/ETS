"""Run the same strict verification cases against source or a relocated frozen CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.core import EvidenceProofBundle
from ets.core.signing import Ed25519TreeHeadSigner

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def command(tmp_path):
    configured = os.environ.get("ETS_VERIFY_EXECUTABLE")
    if configured is None:
        return [sys.executable, "-m", "ets.verifier.cli"]
    executable = Path(configured).resolve()
    assert executable.is_file(), "ETS_VERIFY_EXECUTABLE must identify an existing executable"
    relocated = tmp_path / "relocated runtime with spaces"
    shutil.copytree(executable.parent, relocated)
    return [str(relocated / executable.name)]


def run(command, tmp_path, *args):
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "ETS_VERIFY_BEARER_TOKEN", "ETS_VERIFY_API_KEY"):
        env.pop(key, None)
    if "ETS_VERIFY_EXECUTABLE" in env:
        # An executable invoked by absolute path must not rely on Python on PATH.
        env["PATH"] = os.environ.get("SystemRoot", "/nonexistent")
    else:
        env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [*command, *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert not result.stderr, result.stderr
    return result


@pytest.fixture
def artifacts(tmp_path):
    # Public deterministic test key only, never a deployment credential.
    signer = Ed25519TreeHeadSigner("11" * 32, "standalone-test-key")
    bundle = EvidenceProofBundle.model_validate_json(
        (ROOT / "tests/fixtures/verifier/bundle.json").read_text(encoding="utf-8")
    )
    bundle = bundle.model_copy(update={"tree_head": signer.sign(bundle.tree_head)})
    payload = bundle.model_dump(mode="json")
    trust = {
        "schema_version": "ets.verifier_trust.v1",
        "keys": [
            {
                "key_id": "standalone-test-key",
                "signature_alg": "ed25519",
                "public_key_hex": Ed25519PrivateKey.from_private_bytes(bytes.fromhex("11" * 32))
                .public_key()
                .public_bytes_raw()
                .hex(),
            }
        ],
    }
    bundle_path = tmp_path / "signed bundle.json"
    trust_path = tmp_path / "trusted keys.json"
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    trust_path.write_text(json.dumps(trust), encoding="utf-8")
    return bundle_path, trust_path, payload


def test_standalone_version(command, tmp_path):
    result = run(command, tmp_path, "--version")
    assert result.returncode == 0
    assert result.stdout.startswith("ets-verify ")


def test_standalone_signed_offline_bundle(command, tmp_path, artifacts):
    bundle, trust, _ = artifacts
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["status"] == "valid"
    assert payload["signature_verified"] is True
    assert payload["standing_status"] == "checkpoint_only"
    assert payload["continuity_verified"] is False


def test_standalone_tampered_bundle(command, tmp_path, artifacts):
    bundle, trust, payload = artifacts
    payload["event"]["metadata"]["tampered"] = True
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 1
    assert json.loads(result.stdout)["valid"] is False
    assert json.loads(result.stdout)["status"] == "invalid"


def test_standalone_missing_trust_fails_closed(command, tmp_path, artifacts):
    bundle, _, _ = artifacts
    result = run(command, tmp_path, "offline", str(bundle))
    assert result.returncode == 2
    assert json.loads(result.stdout)["valid"] is False
    assert json.loads(result.stdout)["status"] == "indeterminate"


def test_standalone_untrusted_key_fails_closed(command, tmp_path, artifacts):
    bundle, trust, _ = artifacts
    trust.write_text('{"schema_version":"ets.verifier_trust.v1","keys":[]}', encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 1
    assert json.loads(result.stdout)["signature_verified"] is False
    assert json.loads(result.stdout)["status"] == "indeterminate"


def test_standalone_malformed_input(command, tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text("{", encoding="utf-8")
    result = run(command, tmp_path, "offline", str(path))
    assert result.returncode == 2
    assert json.loads(result.stdout)["valid"] is False
    assert json.loads(result.stdout)["status"] == "malformed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "ets.proof_bundle.v999"),
        ("signature_alg", "future-signature"),
    ],
)
def test_standalone_unsupported_format(command, tmp_path, artifacts, field, value):
    bundle, trust, payload = artifacts
    target = payload["tree_head"] if field == "signature_alg" else payload
    target[field] = value
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "unsupported"
    assert json.loads(result.stdout)["valid"] is False


def test_standalone_tampering_takes_precedence_over_missing_trust(command, tmp_path, artifacts):
    bundle, _, payload = artifacts
    payload["event"]["metadata"]["tampered"] = True
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle))
    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "invalid"


def test_standalone_duplicate_trust_key_is_malformed(command, tmp_path, artifacts):
    bundle, trust, _ = artifacts
    trust.write_text('{"keys":[],"keys":[]}', encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "malformed"


def test_standalone_bad_signature_with_known_key_is_invalid(command, tmp_path, artifacts):
    bundle, trust, payload = artifacts
    payload["tree_head"]["signature"] = "00" * 64
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "invalid"


@pytest.mark.parametrize("part", ["event", "inclusion_proof"])
def test_standalone_unsupported_nested_schema(command, tmp_path, artifacts, part):
    bundle, trust, payload = artifacts
    payload[part]["schema_version"] = "future.v99"
    bundle.write_text(json.dumps(payload), encoding="utf-8")
    result = run(command, tmp_path, "offline", str(bundle), "--trust-store", str(trust))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "unsupported"


def test_standalone_report_export(command, tmp_path, artifacts):
    bundle, _, _ = artifacts
    output = tmp_path / "report.json"
    result = run(command, tmp_path, "certificate", str(bundle), "--out", str(output))
    assert result.returncode == 0, result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["proof_valid"] is True
    assert report["what_this_does_not_verify"]
