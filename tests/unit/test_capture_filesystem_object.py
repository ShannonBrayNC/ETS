from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

import ets.capture.filesystem_object as filesystem_object
from ets.capture.filesystem_object import (
    FilesystemBoundaryUnsupportedError,
    FilesystemObjectInstabilityError,
    FilesystemPathError,
    digest_filesystem_object,
    normalize_relative_object_path,
)
from ets.capture.object_digest import StreamDigestLimitError


def _secure_boundary_supported() -> bool:
    return (
        hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
    )


pytestmark = pytest.mark.skipif(
    not _secure_boundary_supported(),
    reason="host lacks descriptor-relative no-follow traversal",
)


def test_normalize_relative_object_path_accepts_nested_portable_path() -> None:
    assert normalize_relative_object_path("tenant-a/inbox/evidence.bin") == (
        "tenant-a/inbox/evidence.bin"
    )


@pytest.mark.parametrize(
    "relative_path",
    [
        "",
        "/absolute.bin",
        "../escape.bin",
        "nested/../escape.bin",
        "nested/./object.bin",
        "nested//object.bin",
        "nested/object.bin/",
        r"nested\object.bin",
        "C:/object.bin",
        "nested/object:stream",
        "nested/control\x01.bin",
        "nested/cafe\u0301.bin",
        "/".join(["a"] * 65),
    ],
)
def test_normalize_relative_object_path_rejects_unsafe_forms(relative_path: str) -> None:
    with pytest.raises(FilesystemPathError):
        normalize_relative_object_path(relative_path)


def test_digest_filesystem_object_hashes_valid_nested_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "evidence.bin"
    target.parent.mkdir()
    payload = b"bounded-evidence-object"
    target.write_bytes(payload)

    result = digest_filesystem_object(
        tmp_path,
        "nested/evidence.bin",
        maximum_bytes=len(payload),
        chunk_size=7,
    )

    assert result.relative_path == "nested/evidence.bin"
    assert result.digest.value == hashlib.sha256(payload).hexdigest()
    assert result.digest.byte_count == len(payload)
    assert result.observed_before == result.observed_after
    assert result.observed_after.size == len(payload)
    assert result.stability == "no_change_detected"
    assert result.commitment_state == "not_committed"
    assert result.raw_object_retained is False
    assert not hasattr(result, "declared_filename")
    assert not hasattr(result, "source_declared_metadata")


def test_digest_filesystem_object_rejects_exactly_one_byte_over_bound(tmp_path: Path) -> None:
    target = tmp_path / "evidence.bin"
    target.write_bytes(b"x" * 8193)

    with pytest.raises(StreamDigestLimitError, match="declared length"):
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=8192)


def test_digest_filesystem_object_accepts_exact_bound(tmp_path: Path) -> None:
    payload = b"x" * 8192
    target = tmp_path / "evidence.bin"
    target.write_bytes(payload)

    result = digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=8192)

    assert result.digest.byte_count == 8192
    assert result.digest.value == hashlib.sha256(payload).hexdigest()


def test_digest_filesystem_object_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.bin").write_bytes(b"outside-secret")
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(FilesystemPathError, match="safe directory"):
        digest_filesystem_object(tmp_path, "escape/secret.bin", maximum_bytes=1024)


def test_digest_filesystem_object_detects_replacement_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence.bin"
    target.write_bytes(b"original")
    replacement = tmp_path / "replacement.bin"
    replacement.write_bytes(b"replaced")
    original_digest = filesystem_object.digest_stream_sha256

    def replace_then_digest(stream: Any, **kwargs: Any) -> Any:
        os.replace(replacement, target)
        return original_digest(stream, **kwargs)

    monkeypatch.setattr(filesystem_object, "digest_stream_sha256", replace_then_digest)

    with pytest.raises(FilesystemObjectInstabilityError, match="replaced"):
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=1024)


def test_digest_filesystem_object_detects_directory_replacement_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_directory = tmp_path / "nested"
    original_directory.mkdir()
    target = original_directory / "evidence.bin"
    target.write_bytes(b"original")

    replacement_directory = tmp_path / "replacement"
    replacement_directory.mkdir()
    (replacement_directory / "evidence.bin").write_bytes(b"replaced")
    moved_directory = tmp_path / "moved-original"
    original_digest = filesystem_object.digest_stream_sha256

    def replace_directory_then_digest(stream: Any, **kwargs: Any) -> Any:
        original_directory.rename(moved_directory)
        replacement_directory.rename(original_directory)
        return original_digest(stream, **kwargs)

    monkeypatch.setattr(
        filesystem_object,
        "digest_stream_sha256",
        replace_directory_then_digest,
    )

    with pytest.raises(FilesystemObjectInstabilityError, match="directory chain changed"):
        digest_filesystem_object(tmp_path, "nested/evidence.bin", maximum_bytes=1024)


def test_digest_filesystem_object_detects_truncation_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence.bin"
    target.write_bytes(b"original-payload")
    original_digest = filesystem_object.digest_stream_sha256

    def truncate_then_digest(stream: Any, **kwargs: Any) -> Any:
        target.write_bytes(b"short")
        return original_digest(stream, **kwargs)

    monkeypatch.setattr(filesystem_object, "digest_stream_sha256", truncate_then_digest)

    with pytest.raises(FilesystemObjectInstabilityError, match="changed during read"):
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=1024)


def test_digest_filesystem_object_detects_same_inode_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence.bin"
    target.write_bytes(b"aaaaaaaa")
    original_digest = filesystem_object.digest_stream_sha256

    def rewrite_then_digest(stream: Any, **kwargs: Any) -> Any:
        target.write_bytes(b"bbbbbbbb")
        os.utime(target, ns=(1_000_000_000, 1_000_000_000))
        return original_digest(stream, **kwargs)

    monkeypatch.setattr(filesystem_object, "digest_stream_sha256", rewrite_then_digest)

    with pytest.raises(FilesystemObjectInstabilityError, match="metadata changed"):
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=1024)


def test_filesystem_errors_do_not_disclose_raw_content(tmp_path: Path) -> None:
    marker = b"RAW-FILESYSTEM-SECRET-MARKER"
    target = tmp_path / "evidence.bin"
    target.write_bytes(marker)

    with pytest.raises(StreamDigestLimitError) as exc_info:
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=4)

    assert marker.decode() not in str(exc_info.value)


def test_boundary_fails_closed_when_secure_descriptor_traversal_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence.bin"
    target.write_bytes(b"evidence")
    monkeypatch.setattr(filesystem_object.os, "supports_dir_fd", set())

    with pytest.raises(FilesystemBoundaryUnsupportedError, match="descriptor-relative"):
        digest_filesystem_object(tmp_path, "evidence.bin", maximum_bytes=1024)
