import hashlib
import subprocess
from pathlib import Path

import pytest

from ets.ai_witness import SignerError, SubprocessTPMCommandRunner


def test_subprocess_runner_passes_only_digest_and_uses_no_shell(monkeypatch) -> None:
    expected_digest = hashlib.sha256(b"payload").digest()
    observed: dict[str, object] = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        digest_path = Path(command[-1])
        assert digest_path.read_bytes() == expected_digest
        output_index = command.index("-o") + 1
        Path(command[output_index]).write_bytes(b"der-signature")
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = SubprocessTPMCommandRunner()
    signature = runner.sign_digest(
        executable="tpm2_sign",
        key_context="0x81010001",
        digest=expected_digest,
        timeout_seconds=7.5,
    )

    command = observed["command"]
    kwargs = observed["kwargs"]
    assert isinstance(command, list)
    assert command[:5] == ["tpm2_sign", "-Q", "-c", "0x81010001", "-g"]
    assert "-d" in command
    assert ["-s", "ecdsa"] == command[command.index("-s") : command.index("-s") + 2]
    assert kwargs == {"check": False, "capture_output": True, "timeout": 7.5}
    assert signature == b"der-signature"


def test_subprocess_runner_fails_closed_on_timeout(monkeypatch) -> None:
    def fake_timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_timeout)
    runner = SubprocessTPMCommandRunner()

    with pytest.raises(SignerError, match="could not complete"):
        runner.sign_digest(
            executable="tpm2_sign",
            key_context="0x81010001",
            digest=b"x" * 32,
            timeout_seconds=1.0,
        )


def test_subprocess_runner_rejects_non_sha256_digest() -> None:
    runner = SubprocessTPMCommandRunner()
    with pytest.raises(SignerError, match="32-byte SHA-256 digest"):
        runner.sign_digest(
            executable="tpm2_sign",
            key_context="0x81010001",
            digest=b"too-short",
            timeout_seconds=1.0,
        )
