from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ets.connectors.packages import (
    ConnectorPackageActivationError,
    ConnectorPackageActivationPolicy,
    ConnectorPackageCompatibilityError,
    ConnectorPackageIntegrityError,
    ConnectorPackageManifestV1,
    PackageFileDigestV1,
    package_content_sha256,
    verify_connector_package_directory,
)

SAMPLE = Path("examples/connectors/sample_third_party")


def _copy_sample(tmp_path: Path) -> Path:
    target = tmp_path / "package"
    shutil.copytree(SAMPLE, target)
    return target


def test_reference_sample_verifies_without_importing_package_code() -> None:
    package = verify_connector_package_directory(SAMPLE)

    assert package.manifest.package_id == "sample.events.package"
    assert package.manifest.connector_id == "sample.events"
    assert package.definition.connector_id == "sample.events"
    assert package.manifest.publisher.publisher_class == "community_unqualified"


def test_default_activation_policy_rejects_unqualified_community_sample() -> None:
    package = verify_connector_package_directory(SAMPLE)

    with pytest.raises(ConnectorPackageActivationError, match="publisher class"):
        ConnectorPackageActivationPolicy().authorize(package)


def test_explicit_development_policy_can_allow_unqualified_sample() -> None:
    package = verify_connector_package_directory(SAMPLE)
    policy = ConnectorPackageActivationPolicy(
        allowed_publisher_classes=frozenset({"community_unqualified"}),
        require_qualified=False,
    )

    policy.authorize(package)


def test_file_tampering_fails_integrity_before_activation(tmp_path: Path) -> None:
    package_root = _copy_sample(tmp_path)
    (package_root / "sample_connector.py").write_text(
        "raise RuntimeError('tampered')\n",
        encoding="utf-8",
    )

    with pytest.raises(ConnectorPackageIntegrityError, match="integrity mismatch"):
        verify_connector_package_directory(package_root)


def test_undeclared_file_fails_closed(tmp_path: Path) -> None:
    package_root = _copy_sample(tmp_path)
    (package_root / "undeclared.txt").write_text("extra", encoding="utf-8")

    with pytest.raises(ConnectorPackageIntegrityError, match="exactly match"):
        verify_connector_package_directory(package_root)


def test_symlink_inside_package_is_rejected(tmp_path: Path) -> None:
    package_root = _copy_sample(tmp_path)
    target = package_root / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = package_root / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable in this test environment")

    with pytest.raises(ConnectorPackageIntegrityError, match="symlinks"):
        verify_connector_package_directory(package_root)


def test_manifest_rejects_path_traversal_and_unknown_fields() -> None:
    manifest = json.loads((SAMPLE / "connector-package.json").read_text(encoding="utf-8"))
    manifest["definition_path"] = "../definition.json"

    with pytest.raises(ValueError, match="safe relative"):
        ConnectorPackageManifestV1.model_validate(manifest)

    manifest = json.loads((SAMPLE / "connector-package.json").read_text(encoding="utf-8"))
    manifest["unexpected"] = True
    with pytest.raises(ValueError, match="Extra inputs"):
        ConnectorPackageManifestV1.model_validate(manifest)


def test_manifest_requires_entrypoint_modules_to_be_integrity_covered() -> None:
    manifest = json.loads((SAMPLE / "connector-package.json").read_text(encoding="utf-8"))
    manifest["entrypoints"]["adapter"] = "missing_module:Adapter"

    with pytest.raises(ValueError, match="entry point module"):
        ConnectorPackageManifestV1.model_validate(manifest)


def test_incompatible_sdk_gateway_or_capture_contract_fails_closed() -> None:
    with pytest.raises(ConnectorPackageCompatibilityError, match="SDK"):
        verify_connector_package_directory(SAMPLE, sdk_contract_version="ets.connector.sdk.v2")
    with pytest.raises(ConnectorPackageCompatibilityError, match="Gateway"):
        verify_connector_package_directory(SAMPLE, gateway_host_version="ets.gateway.host.v2")
    with pytest.raises(ConnectorPackageCompatibilityError, match="capture"):
        verify_connector_package_directory(SAMPLE, capture_envelope_version="ets.capture.v2")


def test_package_content_digest_is_ordered_and_deterministic() -> None:
    files = (
        PackageFileDigestV1(path="a.py", sha256="a" * 64),
        PackageFileDigestV1(path="b.py", sha256="b" * 64),
    )

    first = package_content_sha256(files)
    second = package_content_sha256(files)

    assert first == second
    assert len(first) == 64
