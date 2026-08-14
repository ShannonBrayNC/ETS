from __future__ import annotations

from pathlib import Path

import pytest

from ets.edge.provisioning import load_or_create_provisioned_local_api_key


def test_default_provisioning_generates_durable_private_key(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"

    first = load_or_create_provisioned_local_api_key(durable_path)
    second = load_or_create_provisioned_local_api_key(durable_path)

    assert first == second
    assert len(first.encode("utf-8")) >= 32
    assert durable_path.stat().st_mode & 0o777 == 0o600


def test_environment_provisioning_preserves_existing_behavior(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    provisioned = "environment-secret-marker-1234567890"

    assert load_or_create_provisioned_local_api_key(durable_path, provisioned) == provisioned
    assert load_or_create_provisioned_local_api_key(durable_path, provisioned) == provisioned


def test_secret_file_provisions_first_boot_and_restart(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "edge-api-key.secret"
    provisioned = "file-secret-marker-1234567890123456"
    secret_path.write_text(f"  {provisioned}\n", encoding="utf-8")

    first = load_or_create_provisioned_local_api_key(
        durable_path,
        explicit_key_file=secret_path,
    )
    second = load_or_create_provisioned_local_api_key(
        durable_path,
        explicit_key_file=secret_path,
    )

    assert first == provisioned
    assert second == provisioned
    assert durable_path.read_text(encoding="utf-8").strip() == provisioned
    assert durable_path.stat().st_mode & 0o777 == 0o600


def test_environment_and_secret_file_are_mutually_exclusive(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "edge-api-key.secret"
    secret_path.write_text("F" * 32, encoding="utf-8")

    with pytest.raises(RuntimeError, match="mutually exclusive"):
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key="E" * 32,
            explicit_key_file=secret_path,
        )

    assert not durable_path.exists()


def test_missing_secret_file_fails_closed(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "missing.secret"

    with pytest.raises(RuntimeError, match="provisioning file is unreadable"):
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key_file=secret_path,
        )

    assert not durable_path.exists()


def test_unreadable_secret_file_fails_closed(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "secret-as-directory"
    secret_path.mkdir()

    with pytest.raises(RuntimeError, match="provisioning file is unreadable"):
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key_file=secret_path,
        )

    assert not durable_path.exists()


@pytest.mark.parametrize("contents", ["", "too-short"])
def test_empty_or_short_secret_file_fails_closed(tmp_path: Path, contents: str) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "edge-api-key.secret"
    secret_path.write_text(contents, encoding="utf-8")

    expected = "provisioning file is empty" if not contents else "at least 32 bytes"
    with pytest.raises(RuntimeError, match=expected):
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key_file=secret_path,
        )

    assert not durable_path.exists()


def test_conflicting_secret_file_cannot_rotate_persisted_key(tmp_path: Path) -> None:
    durable_path = tmp_path / "edge-local-api-key"
    secret_path = tmp_path / "edge-api-key.secret"
    original = "A" * 32
    replacement = "B" * 32
    secret_path.write_text(original, encoding="utf-8")

    assert (
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key_file=secret_path,
        )
        == original
    )

    secret_path.write_text(replacement, encoding="utf-8")
    with pytest.raises(RuntimeError, match="conflicts with persisted credential"):
        load_or_create_provisioned_local_api_key(
            durable_path,
            explicit_key_file=secret_path,
        )

    assert durable_path.read_text(encoding="utf-8").strip() == original
