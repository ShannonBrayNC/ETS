"""Wave 1 Edge Compact R0 provisioning and identity-persistence evidence.

W1-2 is intentionally narrower than a complete HQP-1 run. It captures retained,
machine-readable evidence for R0.1 (provisioning/build identity) and R0.2 (public Edge
device identity persistence across orderly reboots). The resulting evaluation is phase
evidence only and cannot qualify a DUT or execute a physical fault stimulus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.edge.device_identity import EdgeDeviceIdentity, load_device_identity
from ets.qualification.physical_edge import (
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_COMMIT_RE = r"^[0-9a-f]{40,64}$"
_PHASE1_CLAIM_BOUNDARY: Literal[
    "r0_1_r0_2_phase_evidence_not_a_physical_qualification_result"
] = "r0_1_r0_2_phase_evidence_not_a_physical_qualification_result"
_PHASE1_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"


class BootTransition(StrEnum):
    INITIAL_BOOT = "initial_boot"
    ORDERLY_REBOOT = "orderly_reboot"


class StrictPhase1Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeR0ProvisioningReceipt(StrictPhase1Model):
    schema_version: Literal["ets.edge-compact-r0-provisioning-receipt.v1"] = (
        "ets.edge-compact-r0-provisioning-receipt.v1"
    )
    receipt_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    operator_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    installation_method: str = Field(min_length=1, max_length=2048)
    started_at: datetime
    completed_at: datetime
    image_artifact_sha256: str = Field(pattern=_SHA256_RE)
    source_revision: str = Field(pattern=_COMMIT_RE)
    edge_artifact_sha256: str = Field(pattern=_SHA256_RE)
    configuration_sha256: str = Field(pattern=_SHA256_RE)
    install_receipt_sha256: str = Field(pattern=_SHA256_RE)
    secret_scan_sha256: str = Field(pattern=_SHA256_RE)
    observer_receipt_sha256: str = Field(pattern=_SHA256_RE)
    reusable_bootstrap_secret_observed: Literal[False] = False
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "r0_1_r0_2_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE1_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("phase evidence timestamps must include a timezone offset")
        return value

    @model_validator(mode="after")
    def require_monotonic_window(self) -> EdgeR0ProvisioningReceipt:
        if self.completed_at < self.started_at:
            raise ValueError("provisioning completed_at must not precede started_at")
        return self


class EdgeR0IdentitySnapshot(StrictPhase1Model):
    schema_version: Literal["ets.edge-compact-r0-identity-snapshot.v1"] = (
        "ets.edge-compact-r0-identity-snapshot.v1"
    )
    snapshot_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    boot_id: str = Field(min_length=36, max_length=36)
    transition: BootTransition
    observer_id: str = Field(min_length=1, max_length=256)
    observer_receipt_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    identity_manifest_sha256: str = Field(pattern=_SHA256_RE)
    device_id: str = Field(min_length=1, max_length=256)
    signing_algorithm: Literal["ed25519"] = "ed25519"
    signing_public_key_id: str = Field(min_length=1, max_length=256)
    signing_public_key_hex: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_key_fingerprint_sha256: str = Field(pattern=_SHA256_RE)
    key_custody: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "r0_1_r0_2_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE1_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_capture_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("identity snapshot captured_at must include a timezone offset")
        return value

    @field_validator("boot_id")
    @classmethod
    def require_uuid_boot_id(cls, value: str) -> str:
        try:
            parsed = UUID(value)
        except ValueError as exc:
            raise ValueError("boot_id must be a canonical UUID") from exc
        canonical = str(parsed)
        if value.lower() != canonical:
            raise ValueError("boot_id must use canonical UUID formatting")
        return canonical

    @model_validator(mode="after")
    def require_reboot_observer_receipt(self) -> EdgeR0IdentitySnapshot:
        if (
            self.transition is BootTransition.ORDERLY_REBOOT
            and self.observer_receipt_sha256 is None
        ):
            raise ValueError("orderly reboot snapshots require an external observer receipt")
        return self


class EdgeR0Phase1Evaluation(StrictPhase1Model):
    schema_version: Literal["ets.edge-compact-r0-phase1-evaluation.v1"] = (
        "ets.edge-compact-r0-phase1-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    provisioning_receipt_id: str = Field(min_length=1, max_length=256)
    identity_snapshot_ids: tuple[str, ...] = Field(min_length=1)
    r0_1_passed: bool
    r0_2_passed: bool
    phase1_passed: bool
    stable_device_id: str | None = Field(default=None, max_length=256)
    stable_public_key_fingerprint_sha256: str | None = Field(default=None, pattern=_SHA256_RE)
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE1_DISPOSITION
    claim_boundary: Literal[
        "r0_1_r0_2_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE1_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_evaluation_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation timestamp must include a timezone offset")
        return value

    @model_validator(mode="after")
    def enforce_phase_result(self) -> EdgeR0Phase1Evaluation:
        if self.phase1_passed != (self.r0_1_passed and self.r0_2_passed):
            raise ValueError("phase1_passed must equal R0.1 AND R0.2")
        if self.phase1_passed and self.issues:
            raise ValueError("passing phase evaluation cannot retain blocking issues")
        return self


def load_provisioning_receipt(raw: bytes) -> EdgeR0ProvisioningReceipt:
    return EdgeR0ProvisioningReceipt.model_validate_json(raw)


def load_identity_snapshot(raw: bytes) -> EdgeR0IdentitySnapshot:
    return EdgeR0IdentitySnapshot.model_validate_json(raw)


def load_phase1_evaluation(raw: bytes) -> EdgeR0Phase1Evaluation:
    return EdgeR0Phase1Evaluation.model_validate_json(raw)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_provisioning_receipt(
    manifest: EdgeCompactR0BenchManifest,
    *,
    receipt_id: str,
    operator_id: str,
    installation_method: str,
    image_artifact_sha256: str,
    install_receipt_sha256: str,
    secret_scan_sha256: str,
    observer_receipt_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> EdgeR0ProvisioningReceipt:
    blockers = readiness_issues(manifest)
    if blockers:
        rendered = "; ".join(blockers)
        raise ValueError(f"bench manifest is not ready for R0.1 execution: {rendered}")

    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    observer_id = _require_present(manifest.observer.observer_id, "observer_id")
    source_revision = _require_present(manifest.build.source_revision, "source revision").lower()
    edge_artifact = _normalize_sha256(
        _require_present(manifest.build.artifact_digest, "Edge artifact digest")
    )
    configuration = _normalize_sha256(
        _require_present(manifest.build.configuration_digest, "configuration digest")
    )

    return EdgeR0ProvisioningReceipt(
        receipt_id=receipt_id,
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        operator_id=operator_id,
        observer_id=observer_id,
        installation_method=installation_method,
        started_at=started_at,
        completed_at=completed_at,
        image_artifact_sha256=_validate_sha256(image_artifact_sha256),
        source_revision=source_revision,
        edge_artifact_sha256=edge_artifact,
        configuration_sha256=configuration,
        install_receipt_sha256=_validate_sha256(install_receipt_sha256),
        secret_scan_sha256=_validate_sha256(secret_scan_sha256),
        observer_receipt_sha256=_validate_sha256(observer_receipt_sha256),
        reusable_bootstrap_secret_observed=False,
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def build_identity_snapshot(
    manifest: EdgeCompactR0BenchManifest,
    identity: EdgeDeviceIdentity,
    *,
    boot_id: str,
    transition: BootTransition,
    captured_at: datetime,
    observer_receipt_sha256: str | None = None,
) -> EdgeR0IdentitySnapshot:
    blockers = readiness_issues(manifest)
    if blockers:
        rendered = "; ".join(blockers)
        raise ValueError(f"bench manifest is not ready for R0.2 execution: {rendered}")

    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    observer_id = _require_present(manifest.observer.observer_id, "observer_id")
    normalized_observer_receipt = (
        _validate_sha256(observer_receipt_sha256)
        if observer_receipt_sha256 is not None
        else None
    )
    snapshot_seed = {
        "manifest_id": manifest.manifest_id,
        "asset_id": asset_id,
        "boot_id": boot_id,
        "captured_at": captured_at.isoformat(),
        "device_id": identity["device_id"],
        "identity_manifest_sha256": canonical_sha256(identity),
    }
    snapshot_id = f"edge-r0-id-{canonical_sha256(snapshot_seed)[:24]}"

    return EdgeR0IdentitySnapshot(
        snapshot_id=snapshot_id,
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        captured_at=captured_at,
        boot_id=boot_id,
        transition=transition,
        observer_id=observer_id,
        observer_receipt_sha256=normalized_observer_receipt,
        identity_manifest_sha256=canonical_sha256(identity),
        device_id=identity["device_id"],
        signing_algorithm="ed25519",
        signing_public_key_id=identity["signing_public_key_id"],
        signing_public_key_hex=identity["signing_public_key_hex"],
        public_key_fingerprint_sha256=identity["public_key_fingerprint_sha256"],
        key_custody="software_volume",
        hardware_attested=False,
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def evaluate_phase1(
    manifest: EdgeCompactR0BenchManifest,
    receipt: EdgeR0ProvisioningReceipt,
    snapshots: tuple[EdgeR0IdentitySnapshot, ...],
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase1Evaluation:
    r0_1_issues: list[str] = []
    r0_2_issues: list[str] = []

    manifest_blockers = readiness_issues(manifest)
    if manifest_blockers:
        for blocker in manifest_blockers:
            r0_1_issues.append(f"R0.1: bench manifest not ready: {blocker}")
            r0_2_issues.append(f"R0.2: bench manifest not ready: {blocker}")

    asset_id = manifest.dut.asset_id or "unknown-asset"
    observer_id = manifest.observer.observer_id

    if receipt.manifest_id != manifest.manifest_id:
        r0_1_issues.append("R0.1: provisioning receipt manifest_id does not match bench manifest")
    if receipt.asset_id != asset_id:
        r0_1_issues.append("R0.1: provisioning receipt asset_id does not match DUT")
    if observer_id is None or receipt.observer_id != observer_id:
        r0_1_issues.append("R0.1: provisioning observer does not match bench observer")

    source_revision = manifest.build.source_revision
    if source_revision is None or receipt.source_revision != source_revision.lower():
        r0_1_issues.append("R0.1: source revision does not match bench manifest")

    artifact_digest = manifest.build.artifact_digest
    if artifact_digest is None or receipt.edge_artifact_sha256 != _normalize_sha256(
        artifact_digest
    ):
        r0_1_issues.append("R0.1: Edge artifact digest does not match bench manifest")

    configuration_digest = manifest.build.configuration_digest
    if configuration_digest is None or receipt.configuration_sha256 != _normalize_sha256(
        configuration_digest
    ):
        r0_1_issues.append("R0.1: configuration digest does not match bench manifest")

    if len(snapshots) < 2:
        r0_2_issues.append("R0.2: at least two identity snapshots are required")

    snapshot_ids = [item.snapshot_id for item in snapshots]
    if len(snapshot_ids) != len(set(snapshot_ids)):
        r0_2_issues.append("R0.2: identity snapshot IDs must be unique")

    ordered = tuple(sorted(snapshots, key=lambda item: item.captured_at))
    if ordered:
        if ordered[0].transition is not BootTransition.INITIAL_BOOT:
            r0_2_issues.append("R0.2: first identity snapshot must be initial_boot")
        for item in ordered[1:]:
            if item.transition is not BootTransition.ORDERLY_REBOOT:
                r0_2_issues.append(
                    "R0.2: identity snapshots after the baseline must be orderly_reboot"
                )
            if item.observer_receipt_sha256 is None:
                r0_2_issues.append(
                    "R0.2: each orderly reboot snapshot requires external observer evidence"
                )

    boot_ids = {item.boot_id for item in snapshots}
    if len(boot_ids) < 2:
        r0_2_issues.append("R0.2: snapshots must span at least two distinct Linux boot IDs")

    for item in snapshots:
        if item.manifest_id != manifest.manifest_id:
            r0_2_issues.append(
                f"R0.2: snapshot {item.snapshot_id} manifest_id does not match bench manifest"
            )
        if item.asset_id != asset_id:
            r0_2_issues.append(
                f"R0.2: snapshot {item.snapshot_id} asset_id does not match DUT"
            )
        if observer_id is None or item.observer_id != observer_id:
            r0_2_issues.append(
                f"R0.2: snapshot {item.snapshot_id} observer does not match bench observer"
            )
        if item.captured_at < receipt.completed_at:
            r0_2_issues.append(
                f"R0.2: snapshot {item.snapshot_id} predates completed provisioning"
            )
        if item.key_custody != "software_volume" or item.hardware_attested is not False:
            r0_2_issues.append(
                f"R0.2: snapshot {item.snapshot_id} violates the R0 trust boundary"
            )

    stable_fields: tuple[tuple[str, Any], ...] = (
        ("device_id", {item.device_id for item in snapshots}),
        (
            "public_key_fingerprint_sha256",
            {item.public_key_fingerprint_sha256 for item in snapshots},
        ),
        ("signing_public_key_id", {item.signing_public_key_id for item in snapshots}),
        ("signing_public_key_hex", {item.signing_public_key_hex for item in snapshots}),
        ("signing_algorithm", {item.signing_algorithm for item in snapshots}),
        ("key_custody", {item.key_custody for item in snapshots}),
        ("hardware_attested", {item.hardware_attested for item in snapshots}),
    )
    for field_name, values in stable_fields:
        if len(values) > 1:
            r0_2_issues.append(f"R0.2: identity drift detected in {field_name}")

    r0_1_passed = not r0_1_issues
    r0_2_passed = not r0_2_issues
    all_issues = tuple(r0_1_issues + r0_2_issues)
    stable_device_id = snapshots[0].device_id if snapshots and r0_2_passed else None
    stable_fingerprint = (
        snapshots[0].public_key_fingerprint_sha256 if snapshots and r0_2_passed else None
    )
    evaluation_seed = {
        "manifest_id": manifest.manifest_id,
        "receipt_id": receipt.receipt_id,
        "snapshot_ids": sorted(snapshot_ids),
        "evaluated_at": evaluated_at.isoformat(),
    }

    return EdgeR0Phase1Evaluation(
        evaluation_id=f"edge-r0-phase1-{canonical_sha256(evaluation_seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        evaluated_at=evaluated_at,
        provisioning_receipt_id=receipt.receipt_id,
        identity_snapshot_ids=tuple(snapshot_ids),
        r0_1_passed=r0_1_passed,
        r0_2_passed=r0_2_passed,
        phase1_passed=r0_1_passed and r0_2_passed,
        stable_device_id=stable_device_id,
        stable_public_key_fingerprint_sha256=stable_fingerprint,
        issues=all_issues,
        disposition=_PHASE1_DISPOSITION,
        claim_boundary=_PHASE1_CLAIM_BOUNDARY,
    )


def _normalize_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    return _validate_sha256(normalized)


def _validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if re.fullmatch(_SHA256_RE, normalized) is None:
        raise ValueError("expected a 64-character SHA-256 hex digest")
    return normalized


def _require_present(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"missing required {label}")
    return value.strip()


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")
    return parsed


def _read_boot_id(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip().lower()
    UUID(value)
    return value


def _write_json(path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ETS Wave 1 Edge Compact R0 R0.1/R0.2 evidence tooling"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    provision = subparsers.add_parser(
        "record-provisioning",
        help="Record retained R0.1 evidence after operator-controlled provisioning",
    )
    provision.add_argument("--manifest", type=Path, required=True)
    provision.add_argument("--receipt-id", required=True)
    provision.add_argument("--operator-id", required=True)
    provision.add_argument("--installation-method", required=True)
    provision.add_argument("--image-digest", required=True)
    provision.add_argument("--install-receipt", type=Path, required=True)
    provision.add_argument("--secret-scan", type=Path, required=True)
    provision.add_argument("--observer-receipt", type=Path, required=True)
    provision.add_argument("--started-at", required=True)
    provision.add_argument("--completed-at", required=True)
    provision.add_argument("--output", type=Path, required=True)

    snapshot = subparsers.add_parser(
        "capture-identity",
        help="Capture a read-only R0.2 public identity snapshot for the current boot",
    )
    snapshot.add_argument("--manifest", type=Path, required=True)
    snapshot.add_argument("--device-identity", type=Path, required=True)
    snapshot.add_argument(
        "--transition",
        choices=tuple(item.value for item in BootTransition),
        required=True,
    )
    snapshot.add_argument("--observer-receipt", type=Path)
    snapshot.add_argument(
        "--boot-id-file",
        type=Path,
        default=Path("/proc/sys/kernel/random/boot_id"),
    )
    snapshot.add_argument("--captured-at")
    snapshot.add_argument("--output", type=Path, required=True)

    evaluate = subparsers.add_parser(
        "evaluate-phase1",
        help="Evaluate R0.1/R0.2 evidence without making a qualification claim",
    )
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--provisioning-receipt", type=Path, required=True)
    evaluate.add_argument(
        "--identity-snapshot",
        type=Path,
        action="append",
        required=True,
    )
    evaluate.add_argument("--evaluated-at")
    evaluate.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "record-provisioning":
        manifest = load_manifest(args.manifest.read_bytes())
        receipt = build_provisioning_receipt(
            manifest,
            receipt_id=args.receipt_id,
            operator_id=args.operator_id,
            installation_method=args.installation_method,
            image_artifact_sha256=args.image_digest,
            install_receipt_sha256=sha256_file(args.install_receipt),
            secret_scan_sha256=sha256_file(args.secret_scan),
            observer_receipt_sha256=sha256_file(args.observer_receipt),
            started_at=_parse_datetime(args.started_at),
            completed_at=_parse_datetime(args.completed_at),
        )
        _write_json(args.output, receipt)
        return 0

    if args.command == "capture-identity":
        manifest = load_manifest(args.manifest.read_bytes())
        identity = load_device_identity(args.device_identity)
        observer_receipt = (
            sha256_file(args.observer_receipt)
            if args.observer_receipt is not None
            else None
        )
        captured_at = (
            _parse_datetime(args.captured_at)
            if args.captured_at is not None
            else datetime.now(UTC)
        )
        identity_snapshot = build_identity_snapshot(
            manifest,
            identity,
            boot_id=_read_boot_id(args.boot_id_file),
            transition=BootTransition(args.transition),
            captured_at=captured_at,
            observer_receipt_sha256=observer_receipt,
        )
        _write_json(args.output, identity_snapshot)
        return 0

    if args.command == "evaluate-phase1":
        manifest = load_manifest(args.manifest.read_bytes())
        receipt = load_provisioning_receipt(args.provisioning_receipt.read_bytes())
        identity_snapshots = tuple(
            load_identity_snapshot(path.read_bytes()) for path in args.identity_snapshot
        )
        evaluated_at = (
            _parse_datetime(args.evaluated_at)
            if args.evaluated_at is not None
            else datetime.now(UTC)
        )
        result = evaluate_phase1(
            manifest,
            receipt,
            identity_snapshots,
            evaluated_at=evaluated_at,
        )
        _write_json(args.output, result)
        return 0 if result.phase1_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")
