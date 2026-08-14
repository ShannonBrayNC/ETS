"""Race-resistant filesystem object intake for bounded evidence capture."""

from __future__ import annotations

import os
import stat
import unicodedata
from dataclasses import dataclass
from typing import Final

from ets.capture.object_digest import (
    StreamDigestLengthError,
    StreamDigestResult,
    digest_stream_sha256,
)

MAX_RELATIVE_PATH_CHARS: Final = 4096
MAX_RELATIVE_PATH_COMPONENTS: Final = 64


class FilesystemObjectError(ValueError):
    """Base error for filesystem object intake failures."""


class FilesystemPathError(FilesystemObjectError):
    """Raised when an intake path violates the configured boundary."""


class FilesystemObjectInstabilityError(FilesystemObjectError):
    """Raised when collector-observed source identity or metadata changes."""


class FilesystemBoundaryUnsupportedError(FilesystemObjectError):
    """Raised when the host cannot provide the required no-follow traversal."""


class FilesystemReadError(FilesystemObjectError):
    """Raised when a bounded filesystem operation fails without source disclosure."""


@dataclass(frozen=True, slots=True)
class FilesystemObjectMetadata:
    """Collector-observed metadata for one opened filesystem object."""

    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True, slots=True)
class FilesystemObjectDigest:
    """Digest plus collector observations without durable-commit claims."""

    relative_path: str
    digest: StreamDigestResult
    observed_before: FilesystemObjectMetadata
    observed_after: FilesystemObjectMetadata
    stability: str = "no_change_detected"
    commitment_state: str = "not_committed"
    raw_object_retained: bool = False


@dataclass(frozen=True, slots=True)
class _DirectoryStep:
    parent_fd: int
    component: str
    opened: os.stat_result


def normalize_relative_object_path(relative_path: str) -> str:
    """Validate the portable, normalized relative-path contract."""

    if not isinstance(relative_path, str):
        raise TypeError("relative_path must be a string")
    if not relative_path:
        raise FilesystemPathError("relative path must not be empty")
    if len(relative_path) > MAX_RELATIVE_PATH_CHARS:
        raise FilesystemPathError("relative path exceeds configured path limit")
    if "\x00" in relative_path:
        raise FilesystemPathError("relative path contains a forbidden character")
    if "\\" in relative_path:
        raise FilesystemPathError("relative path must use forward-slash separators")
    if unicodedata.normalize("NFC", relative_path) != relative_path:
        raise FilesystemPathError("relative path must use NFC normalization")
    if relative_path.startswith("/") or relative_path.endswith("/"):
        raise FilesystemPathError("relative path must name one object below the intake root")

    parts = relative_path.split("/")
    if len(parts) > MAX_RELATIVE_PATH_COMPONENTS:
        raise FilesystemPathError("relative path exceeds configured component limit")
    for part in parts:
        if part in {"", ".", ".."}:
            raise FilesystemPathError("relative path contains an unsafe path component")
        if ":" in part:
            raise FilesystemPathError("relative path contains an unsupported path component")
        if any(ord(character) < 32 or ord(character) == 127 for character in part):
            raise FilesystemPathError("relative path contains a forbidden character")

    return "/".join(parts)


def digest_filesystem_object(
    intake_root: str | os.PathLike[str],
    relative_path: str,
    *,
    maximum_bytes: int,
    chunk_size: int = 64 * 1024,
) -> FilesystemObjectDigest:
    """Hash one regular file through a no-follow, descriptor-relative boundary."""

    normalized = normalize_relative_object_path(relative_path)
    _require_secure_descriptor_traversal()

    root_path = os.path.abspath(os.fspath(intake_root))
    root_fd, root_opened = _open_root(root_path)
    opened_fds = [root_fd]
    directory_steps: list[_DirectoryStep] = []
    parent_fd = root_fd

    try:
        parts = normalized.split("/")
        for component in parts[:-1]:
            child_fd, child_opened = _open_directory_component(parent_fd, component)
            opened_fds.append(child_fd)
            directory_steps.append(
                _DirectoryStep(
                    parent_fd=parent_fd,
                    component=component,
                    opened=child_opened,
                )
            )
            parent_fd = child_fd

        result = _digest_final_component(
            parent_fd,
            parts[-1],
            normalized,
            maximum_bytes=maximum_bytes,
            chunk_size=chunk_size,
        )
        _verify_directory_chain(root_path, root_opened, directory_steps)
        return result
    finally:
        for descriptor in reversed(opened_fds):
            os.close(descriptor)


def _require_secure_descriptor_traversal() -> None:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise FilesystemBoundaryUnsupportedError(
            "host does not support the required no-follow filesystem boundary"
        )
    if os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        raise FilesystemBoundaryUnsupportedError(
            "host does not support descriptor-relative filesystem traversal"
        )


def _open_root(root_path: str) -> tuple[int, os.stat_result]:
    try:
        before = os.lstat(root_path)
    except OSError as exc:
        raise FilesystemReadError("intake root is unavailable") from exc

    if _is_link_or_reparse(before) or not stat.S_ISDIR(before.st_mode):
        raise FilesystemPathError("intake root must be a non-link directory")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        root_fd = os.open(root_path, flags)
    except OSError as exc:
        raise FilesystemReadError("intake root could not be opened safely") from exc

    opened = os.fstat(root_fd)
    if not _same_identity(before, opened) or not stat.S_ISDIR(opened.st_mode):
        os.close(root_fd)
        raise FilesystemObjectInstabilityError("intake root changed during open")
    return root_fd, opened


def _open_directory_component(
    parent_fd: int,
    component: str,
) -> tuple[int, os.stat_result]:
    try:
        before = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise FilesystemReadError("filesystem path component is unavailable") from exc

    if _is_link_or_reparse(before) or not stat.S_ISDIR(before.st_mode):
        raise FilesystemPathError("filesystem path component is not a safe directory")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        child_fd = os.open(component, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise FilesystemReadError("filesystem path component could not be opened safely") from exc

    opened = os.fstat(child_fd)
    if not _same_identity(before, opened) or not stat.S_ISDIR(opened.st_mode):
        os.close(child_fd)
        raise FilesystemObjectInstabilityError("filesystem path changed during traversal")
    return child_fd, opened


def _digest_final_component(
    parent_fd: int,
    file_name: str,
    normalized_path: str,
    *,
    maximum_bytes: int,
    chunk_size: int,
) -> FilesystemObjectDigest:
    try:
        path_before = os.stat(file_name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise FilesystemReadError("filesystem object is unavailable") from exc

    if _is_link_or_reparse(path_before) or not stat.S_ISREG(path_before.st_mode):
        raise FilesystemPathError("filesystem object must be a non-link regular file")

    try:
        file_fd = os.open(file_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise FilesystemReadError("filesystem object could not be opened safely") from exc

    try:
        opened_before = os.fstat(file_fd)
        if (
            not _same_identity(path_before, opened_before)
            or not stat.S_ISREG(opened_before.st_mode)
        ):
            raise FilesystemObjectInstabilityError("filesystem object changed during open")

        before = _metadata(opened_before)
        try:
            with os.fdopen(file_fd, "rb", closefd=False) as stream:
                digest = digest_stream_sha256(
                    stream,
                    maximum_bytes=maximum_bytes,
                    chunk_size=chunk_size,
                    declared_length=before.size,
                )
                opened_after = os.fstat(file_fd)
        except StreamDigestLengthError as exc:
            raise FilesystemObjectInstabilityError("filesystem object changed during read") from exc
        except OSError as exc:
            raise FilesystemReadError("filesystem object read failed") from exc

        try:
            path_after = os.stat(file_name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise FilesystemObjectInstabilityError("filesystem object changed after read") from exc

        if _is_link_or_reparse(path_after) or not stat.S_ISREG(path_after.st_mode):
            raise FilesystemObjectInstabilityError("filesystem object changed after read")

        after = _metadata(opened_after)
        if not _same_identity(opened_before, opened_after):
            raise FilesystemObjectInstabilityError("filesystem object identity changed during read")
        if not _same_identity(opened_before, path_after):
            raise FilesystemObjectInstabilityError("filesystem object was replaced during read")
        if before != after or _metadata(path_after) != after:
            raise FilesystemObjectInstabilityError("filesystem object metadata changed during read")
        if digest.byte_count != after.size:
            raise FilesystemObjectInstabilityError("filesystem object size changed during read")

        return FilesystemObjectDigest(
            relative_path=normalized_path,
            digest=digest,
            observed_before=before,
            observed_after=after,
        )
    finally:
        os.close(file_fd)


def _verify_directory_chain(
    root_path: str,
    root_opened: os.stat_result,
    directory_steps: list[_DirectoryStep],
) -> None:
    try:
        root_after = os.lstat(root_path)
    except OSError as exc:
        raise FilesystemObjectInstabilityError("intake root changed after read") from exc

    if (
        _is_link_or_reparse(root_after)
        or not stat.S_ISDIR(root_after.st_mode)
        or not _same_identity(root_opened, root_after)
    ):
        raise FilesystemObjectInstabilityError("intake root changed after read")

    for step in directory_steps:
        try:
            current = os.stat(
                step.component,
                dir_fd=step.parent_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise FilesystemObjectInstabilityError(
                "filesystem directory chain changed after read"
            ) from exc

        if (
            _is_link_or_reparse(current)
            or not stat.S_ISDIR(current.st_mode)
            or not _same_identity(step.opened, current)
        ):
            raise FilesystemObjectInstabilityError(
                "filesystem directory chain changed after read"
            )


def _metadata(value: os.stat_result) -> FilesystemObjectMetadata:
    return FilesystemObjectMetadata(
        device=value.st_dev,
        inode=value.st_ino,
        size=value.st_size,
        mtime_ns=value.st_mtime_ns,
        ctime_ns=value.st_ctime_ns,
    )


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _is_link_or_reparse(value: os.stat_result) -> bool:
    if stat.S_ISLNK(value.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(value, "st_file_attributes", 0)
    return bool(reparse_flag and file_attributes & reparse_flag)
