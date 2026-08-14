"""Integrity and provenance contract for third-party ETS connector packages."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from ets.connectors.models import (
    CAPTURE_ENVELOPE_VERSION,
    CONNECTOR_SDK_CONTRACT_VERSION,
    GATEWAY_CONNECTOR_HOST_VERSION,
    ConnectorDefinitionV1,
)

CONNECTOR_PACKAGE_SCHEMA_VERSION = "ets.connector.package.v1"

PublisherClass = Literal[
    "lantern_builtin",
    "lantern_qualified_third_party",
    "community_unqualified",
]
QualificationState = Literal["qualified", "unqualified", "revoked"]

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")
_ENTRY_POINT_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ConnectorPackageError(ValueError):
    """Base failure for package manifest/integrity/activation validation."""


class ConnectorPackageIntegrityError(ConnectorPackageError):
    """Raised when package contents do not match the declared integrity set."""


class ConnectorPackageCompatibilityError(ConnectorPackageError):
    """Raised when package compatibility does not match the local connector host."""


class ConnectorPackageActivationError(ConnectorPackageError):
    """Raised when package policy does not permit activation."""


class PackageFileDigestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=300)
    sha256: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        _validate_relative_package_path(value)
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("package file sha256 must be 64 lowercase hexadecimal characters")
        return normalized


class ConnectorPackagePublisherV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=200)
    publisher_class: PublisherClass
    qualification_state: QualificationState

    @model_validator(mode="after")
    def validate_classification(self) -> ConnectorPackagePublisherV1:
        if self.publisher_class == "community_unqualified" and self.qualification_state == "qualified":
            raise ValueError("community_unqualified packages cannot claim qualified state")
        return self


class ConnectorPackageProvenanceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_url: HttpUrl
    source_revision: str = Field(min_length=7, max_length=128)
    build_ref: str | None = Field(default=None, min_length=1, max_length=200)


class ConnectorPackageCompatibilityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sdk_contract_version: str
    gateway_host_versions: tuple[str, ...] = Field(min_length=1, max_length=16)
    capture_envelope_versions: tuple[str, ...] = Field(min_length=1, max_length=16)


class ConnectorPackageEntrypointsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter: str
    conformance: str

    @field_validator("adapter", "conformance")
    @classmethod
    def validate_entry_point(cls, value: str) -> str:
        if not _ENTRY_POINT_PATTERN.fullmatch(value):
            raise ValueError("connector package entry point must use module.path:attribute syntax")
        return value


class ConnectorPackageManifestV1(BaseModel):
    """Static package manifest; validation never imports package code."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["ets.connector.package.v1"]
    package_id: str
    package_version: str
    connector_id: str
    publisher: ConnectorPackagePublisherV1
    provenance: ConnectorPackageProvenanceV1
    compatibility: ConnectorPackageCompatibilityV1
    definition_path: str
    settings_schema_path: str
    entrypoints: ConnectorPackageEntrypointsV1
    files: tuple[PackageFileDigestV1, ...] = Field(min_length=1, max_length=1000)
    package_content_sha256: str

    @field_validator("package_id", "connector_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("package and connector ids must use lowercase safe identifiers")
        return value

    @field_validator("package_version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _VERSION_PATTERN.fullmatch(value):
            raise ValueError("package_version is invalid")
        return value

    @field_validator("definition_path", "settings_schema_path")
    @classmethod
    def validate_manifest_path(cls, value: str) -> str:
        _validate_relative_package_path(value)
        return value

    @field_validator("package_content_sha256")
    @classmethod
    def validate_content_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("package_content_sha256 must be lowercase SHA-256 hex")
        return normalized

    @model_validator(mode="after")
    def validate_file_set(self) -> ConnectorPackageManifestV1:
        paths = [item.path for item in self.files]
        if paths != sorted(paths):
            raise ValueError("connector package files must be sorted by path")
        if len(paths) != len(set(paths)):
            raise ValueError("connector package files must not contain duplicate paths")
        required = {self.definition_path, self.settings_schema_path}
        missing = required - set(paths)
        if missing:
            raise ValueError("connector package definition/settings schema must be integrity-covered")
        for entrypoint in (self.entrypoints.adapter, self.entrypoints.conformance):
            module_path = _module_file_for_entrypoint(entrypoint)
            if module_path not in paths:
                raise ValueError("connector package entry point module must be integrity-covered")
        return self


@dataclass(frozen=True, slots=True)
class VerifiedConnectorPackage:
    root: Path
    manifest: ConnectorPackageManifestV1
    definition: ConnectorDefinitionV1


@dataclass(frozen=True, slots=True)
class ConnectorPackageActivationPolicy:
    """Explicit host policy; package integrity alone never grants activation."""

    allowed_publisher_classes: frozenset[PublisherClass] = frozenset(
        {"lantern_qualified_third_party"}
    )
    require_qualified: bool = True

    def authorize(self, package: VerifiedConnectorPackage) -> None:
        publisher = package.manifest.publisher
        if publisher.publisher_class not in self.allowed_publisher_classes:
            raise ConnectorPackageActivationError(
                "connector package publisher class is not permitted for activation"
            )
        if self.require_qualified and publisher.qualification_state != "qualified":
            raise ConnectorPackageActivationError(
                "connector package has not completed the required qualification state"
            )
        if publisher.qualification_state == "revoked":
            raise ConnectorPackageActivationError("connector package qualification is revoked")


def verify_connector_package_directory(
    root: Path,
    *,
    manifest_name: str = "connector-package.json",
    sdk_contract_version: str = CONNECTOR_SDK_CONTRACT_VERSION,
    gateway_host_version: str = GATEWAY_CONNECTOR_HOST_VERSION,
    capture_envelope_version: str = CAPTURE_ENVELOPE_VERSION,
) -> VerifiedConnectorPackage:
    """Verify one package directory without importing or executing package code."""

    if root.is_symlink() or not root.is_dir():
        raise ConnectorPackageIntegrityError("connector package root must be a real directory")
    _validate_relative_package_path(manifest_name)
    manifest_path = root / manifest_name
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ConnectorPackageIntegrityError("connector package manifest is missing or unsafe")
    try:
        manifest = ConnectorPackageManifestV1.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise ConnectorPackageIntegrityError("connector package manifest is invalid") from exc

    actual_paths = _enumerate_package_files(root, exclude=manifest_name)
    declared_paths = tuple(item.path for item in manifest.files)
    if actual_paths != declared_paths:
        raise ConnectorPackageIntegrityError(
            "connector package contents do not exactly match the integrity manifest"
        )

    actual_digests: list[PackageFileDigestV1] = []
    for declared in manifest.files:
        path = root / PurePosixPath(declared.path)
        digest = _sha256_file(path)
        if digest != declared.sha256:
            raise ConnectorPackageIntegrityError(
                f"connector package file integrity mismatch: {declared.path}"
            )
        actual_digests.append(PackageFileDigestV1(path=declared.path, sha256=digest))

    aggregate = package_content_sha256(tuple(actual_digests))
    if aggregate != manifest.package_content_sha256:
        raise ConnectorPackageIntegrityError("connector package aggregate integrity mismatch")

    _check_compatibility(
        manifest,
        sdk_contract_version=sdk_contract_version,
        gateway_host_version=gateway_host_version,
        capture_envelope_version=capture_envelope_version,
    )
    definition_path = root / PurePosixPath(manifest.definition_path)
    try:
        definition = ConnectorDefinitionV1.model_validate_json(
            definition_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise ConnectorPackageIntegrityError("connector definition is invalid") from exc
    if definition.connector_id != manifest.connector_id:
        raise ConnectorPackageIntegrityError(
            "connector package connector_id does not match definition connector_id"
        )
    if definition.sdk_contract_version != manifest.compatibility.sdk_contract_version:
        raise ConnectorPackageCompatibilityError(
            "connector definition and package SDK compatibility declarations differ"
        )

    settings_path = root / PurePosixPath(manifest.settings_schema_path)
    try:
        settings_schema = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorPackageIntegrityError("connector settings schema is invalid JSON") from exc
    if not isinstance(settings_schema, dict):
        raise ConnectorPackageIntegrityError("connector settings schema must be a JSON object")

    return VerifiedConnectorPackage(root=root, manifest=manifest, definition=definition)


def package_content_sha256(files: tuple[PackageFileDigestV1, ...]) -> str:
    """Hash a canonical sorted file-integrity inventory."""

    payload = json.dumps(
        [{"path": item.path, "sha256": item.sha256} for item in files],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _enumerate_package_files(root: Path, *, exclude: str) -> tuple[str, ...]:
    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == exclude:
            continue
        if path.is_symlink():
            raise ConnectorPackageIntegrityError(
                f"connector package symlinks are not permitted: {relative}"
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise ConnectorPackageIntegrityError(
                f"connector package special files are not permitted: {relative}"
            )
        _validate_relative_package_path(relative)
        paths.append(relative)
    return tuple(paths)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_compatibility(
    manifest: ConnectorPackageManifestV1,
    *,
    sdk_contract_version: str,
    gateway_host_version: str,
    capture_envelope_version: str,
) -> None:
    compatibility = manifest.compatibility
    if compatibility.sdk_contract_version != sdk_contract_version:
        raise ConnectorPackageCompatibilityError("connector package SDK contract is incompatible")
    if gateway_host_version not in compatibility.gateway_host_versions:
        raise ConnectorPackageCompatibilityError("connector package Gateway host is incompatible")
    if capture_envelope_version not in compatibility.capture_envelope_versions:
        raise ConnectorPackageCompatibilityError("connector package capture envelope is incompatible")


def _module_file_for_entrypoint(entrypoint: str) -> str:
    module, _, _attribute = entrypoint.partition(":")
    return f"{module.replace('.', '/')}.py"


def _validate_relative_package_path(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("connector package path must be a safe relative POSIX path")
    if not path.parts or any(part == "" for part in path.parts):
        raise ValueError("connector package path is invalid")
