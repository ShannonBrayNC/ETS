"""Wave 1 physical Edge Compact R0 bench bootstrap.

This module deliberately stops before fault injection. It may inspect the local Linux
host using read-only interfaces, build a draft named-DUT/bench manifest, and determine
whether the operator has supplied enough claim-critical information to begin the HQP-3
physical corpus. It never performs power cuts, time changes, storage filling, network
impairment, firmware changes, or recovery/reimage actions.

A complete bench manifest is *bench readiness*, not a hardware qualification result.
Physical qualification still requires an HQP-1 run package and HQP-2 independent
verification under the Edge corpus.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

R0_SCHEMA_VERSION = "ets.edge-compact-r0-bench-manifest.v1"
R0_QUALIFICATION_CLASS = "EDGE_COMPACT_R0"
HQP_VERIFY_COMMAND = "python -m ets.hqp_verify"
_REQUIRED_CONTROL_KINDS = {"power", "network", "storage", "clock", "recovery"}
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ManifestState(StrEnum):
    DRAFT = "draft"
    READY_FOR_QUALIFICATION = "ready_for_qualification"


class BenchControlKind(StrEnum):
    POWER = "power"
    NETWORK = "network"
    STORAGE = "storage"
    CLOCK = "clock"
    RECOVERY = "recovery"


class StrictR0Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class StorageDevice(StrictR0Model):
    name: str = Field(min_length=1, max_length=256)
    vendor: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=512)
    serial: str | None = Field(default=None, max_length=512)
    firmware: str | None = Field(default=None, max_length=512)
    size_bytes: int | None = Field(default=None, ge=0)
    transport: str | None = Field(default=None, max_length=128)


class NetworkInterface(StrictR0Model):
    name: str = Field(min_length=1, max_length=256)
    mac_address: str | None = Field(default=None, max_length=128)
    driver: str | None = Field(default=None, max_length=256)
    firmware: str | None = Field(default=None, max_length=512)


class EdgeR0Dut(StrictR0Model):
    manufacturer: str | None = Field(default=None, max_length=512)
    model: str | None = Field(default=None, max_length=512)
    hardware_revision: str | None = Field(default=None, max_length=512)
    asset_id: str | None = Field(default=None, max_length=256)
    cpu_architecture: str = Field(min_length=1, max_length=128)
    cpu_model: str | None = Field(default=None, max_length=512)
    memory_bytes: int | None = Field(default=None, ge=0)
    storage: tuple[StorageDevice, ...] = ()
    network: tuple[NetworkInterface, ...] = ()
    firmware: dict[str, str] = Field(default_factory=dict)
    claim_critical_fields_confirmed_by_operator: bool = False


class EdgeRuntimeBinding(StrictR0Model):
    os_id: str | None = Field(default=None, max_length=128)
    os_version_id: str | None = Field(default=None, max_length=128)
    os_pretty_name: str | None = Field(default=None, max_length=512)
    kernel_release: str = Field(min_length=1, max_length=256)
    python_version: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=256)


class EdgeBuildBinding(StrictR0Model):
    source_revision: str | None = Field(default=None, max_length=256)
    artifact_digest: str | None = Field(default=None, max_length=256)
    configuration_digest: str | None = Field(default=None, max_length=256)

    @field_validator("artifact_digest", "configuration_digest")
    @classmethod
    def validate_digest_shape(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError(
                "digest must be a 64-character SHA-256 hex value, optionally prefixed sha256:"
            )
        return value


class EdgeR0TrustPosture(StrictR0Model):
    identity_profile: Literal["software_volume"] = "software_volume"
    hardware_attested: Literal[False] = False
    secure_boot_verified: Literal[False] = False
    hardware_key_protection: Literal[False] = False


class IndependentObserver(StrictR0Model):
    observer_id: str | None = Field(default=None, max_length=256)
    observer_host_id: str | None = Field(default=None, max_length=256)
    observation_method: str | None = Field(default=None, max_length=2048)
    independent_from_dut: bool = False


class IndependentVerifier(StrictR0Model):
    verifier_host_id: str | None = Field(default=None, max_length=256)
    verifier_identity: str | None = Field(default=None, max_length=256)
    command: Literal["python -m ets.hqp_verify"] = HQP_VERIFY_COMMAND
    independent_from_dut: bool = False


class BenchControl(StrictR0Model):
    kind: BenchControlKind
    control_id: str = Field(min_length=1, max_length=256)
    method: str | None = Field(default=None, max_length=2048)
    independent_observation_method: str | None = Field(default=None, max_length=2048)
    destructive_or_disruptive: bool
    operator_approval_required: bool
    bootstrap_cli_executes_action: Literal[False] = False

    @model_validator(mode="after")
    def require_operator_gate_for_disruptive_control(self) -> BenchControl:
        if self.destructive_or_disruptive and not self.operator_approval_required:
            raise ValueError(
                "destructive/disruptive bench controls require explicit operator approval"
            )
        return self


class EdgeCompactR0BenchManifest(StrictR0Model):
    schema_version: Literal["ets.edge-compact-r0-bench-manifest.v1"] = R0_SCHEMA_VERSION
    manifest_id: str = Field(min_length=1, max_length=256)
    qualification_class: Literal["EDGE_COMPACT_R0"] = R0_QUALIFICATION_CLASS
    manifest_state: ManifestState = ManifestState.DRAFT
    collected_at: datetime
    dut: EdgeR0Dut
    runtime: EdgeRuntimeBinding
    build: EdgeBuildBinding
    trust: EdgeR0TrustPosture = Field(default_factory=EdgeR0TrustPosture)
    observer: IndependentObserver = Field(default_factory=IndependentObserver)
    verifier: IndependentVerifier = Field(default_factory=IndependentVerifier)
    controls: tuple[BenchControl, ...]
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_unique_controls(self) -> EdgeCompactR0BenchManifest:
        kinds = [control.kind for control in self.controls]
        if len(kinds) != len(set(kinds)):
            raise ValueError("bench control kinds must be unique")
        return self


def load_manifest(raw: bytes) -> EdgeCompactR0BenchManifest:
    """Load a strict R0 manifest without implying that it is ready."""

    return EdgeCompactR0BenchManifest.model_validate_json(raw)


def readiness_issues(manifest: EdgeCompactR0BenchManifest) -> tuple[str, ...]:
    """Return deterministic blockers that prevent starting physical HQP execution."""

    issues: list[str] = []
    dut = manifest.dut

    if manifest.manifest_state is not ManifestState.READY_FOR_QUALIFICATION:
        issues.append("manifest_state must be ready_for_qualification before physical execution")

    if dut.cpu_architecture.lower() not in {"x86_64", "amd64"}:
        issues.append("DUT CPU architecture must be x86-64/amd64 for EDGE_COMPACT_R0")

    critical_identity = {
        "dut.manufacturer": dut.manufacturer,
        "dut.model": dut.model,
        "dut.hardware_revision": dut.hardware_revision,
        "dut.asset_id": dut.asset_id,
        "dut.cpu_model": dut.cpu_model,
    }
    for label, value in critical_identity.items():
        if not _present(value):
            issues.append(f"missing claim-critical field: {label}")

    if not dut.claim_critical_fields_confirmed_by_operator:
        issues.append("claim-critical DUT fields have not been confirmed by an operator")

    if dut.memory_bytes is None or dut.memory_bytes <= 0:
        issues.append("DUT memory capacity is missing")

    if not dut.storage:
        issues.append("no physical storage device is recorded")
    elif not any(_complete_storage_identity(item) for item in dut.storage):
        issues.append(
            "no storage device has complete vendor/model/firmware/capacity identity"
        )

    if not dut.network:
        issues.append("no network interface is recorded")

    bios_version = dut.firmware.get("bios_version") or dut.firmware.get("uefi_version")
    if not _present(bios_version):
        issues.append("BIOS/UEFI firmware version is missing")

    runtime = manifest.runtime
    if not _present(runtime.os_id):
        issues.append("operating-system identifier is missing")
    if not _present(runtime.os_version_id):
        issues.append("operating-system version is missing")

    if not _present(manifest.build.source_revision):
        issues.append("Edge source revision is missing")
    if not _present(manifest.build.artifact_digest):
        issues.append("Edge artifact SHA-256 digest is missing")
    if not _present(manifest.build.configuration_digest):
        issues.append("Edge configuration SHA-256 digest is missing")

    if not manifest.observer.independent_from_dut:
        issues.append("external observer is not declared independent from the DUT")
    if not _present(manifest.observer.observer_id):
        issues.append("external observer identity is missing")
    if not _present(manifest.observer.observer_host_id):
        issues.append("external observer host identity is missing")
    if not _present(manifest.observer.observation_method):
        issues.append("external observation method is missing")

    if not manifest.verifier.independent_from_dut:
        issues.append("HQP verifier is not declared independent from the DUT")
    if not _present(manifest.verifier.verifier_host_id):
        issues.append("HQP verifier host identity is missing")
    if not _present(manifest.verifier.verifier_identity):
        issues.append("HQP verifier identity is missing")

    if dut.asset_id and dut.asset_id in {
        manifest.observer.observer_host_id,
        manifest.verifier.verifier_host_id,
    }:
        issues.append("DUT asset_id must not also identify the observer/verifier host")

    controls = {control.kind.value: control for control in manifest.controls}
    for kind in sorted(_REQUIRED_CONTROL_KINDS):
        control = controls.get(kind)
        if control is None:
            issues.append(f"missing required bench control: {kind}")
            continue
        if not _present(control.method):
            issues.append(f"bench control {kind} has no execution method")
        if not _present(control.independent_observation_method):
            issues.append(f"bench control {kind} has no independent observation method")

    if manifest.manifest_state is ManifestState.READY_FOR_QUALIFICATION and issues:
        issues.append("manifest declares ready_for_qualification while readiness blockers remain")

    return tuple(issues)


def assert_ready_for_qualification(manifest: EdgeCompactR0BenchManifest) -> None:
    issues = readiness_issues(manifest)
    if issues:
        rendered = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"Edge Compact R0 bench manifest is not ready:\n{rendered}")


def fingerprint_local_linux(
    *,
    manifest_id: str | None = None,
    asset_id: str | None = None,
) -> EdgeCompactR0BenchManifest:
    """Create a read-only best-effort draft fingerprint of the local host.

    The function reads procfs/sysfs and invokes read-only inventory commands when they
    are available. It never changes the host or qualification environment.
    """

    now = datetime.now(UTC)
    hostname = socket.gethostname() or "unknown-host"
    if manifest_id is None:
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        manifest_id = f"edge-r0-draft-{_safe_id(hostname)}-{stamp}"

    firmware = _collect_firmware()
    storage = _collect_storage()
    network = _collect_network()
    os_release = _parse_os_release()

    dut = EdgeR0Dut(
        manufacturer=_read_sysfs_text("/sys/class/dmi/id/sys_vendor"),
        model=_read_sysfs_text("/sys/class/dmi/id/product_name"),
        hardware_revision=(
            _read_sysfs_text("/sys/class/dmi/id/product_version")
            or _read_sysfs_text("/sys/class/dmi/id/board_version")
        ),
        asset_id=asset_id,
        cpu_architecture=platform.machine() or "unknown",
        cpu_model=_cpu_model(),
        memory_bytes=_memory_bytes(),
        storage=storage,
        network=network,
        firmware=firmware,
        claim_critical_fields_confirmed_by_operator=False,
    )

    runtime = EdgeRuntimeBinding(
        os_id=os_release.get("ID"),
        os_version_id=os_release.get("VERSION_ID"),
        os_pretty_name=os_release.get("PRETTY_NAME"),
        kernel_release=platform.release() or "unknown",
        python_version=platform.python_version(),
        hostname=hostname,
    )

    build = EdgeBuildBinding(
        source_revision=_git_revision(),
        artifact_digest=None,
        configuration_digest=None,
    )

    return EdgeCompactR0BenchManifest(
        schema_version=R0_SCHEMA_VERSION,
        manifest_id=manifest_id,
        qualification_class=R0_QUALIFICATION_CLASS,
        manifest_state=ManifestState.DRAFT,
        collected_at=now,
        dut=dut,
        runtime=runtime,
        build=build,
        trust=EdgeR0TrustPosture(),
        observer=IndependentObserver(),
        verifier=IndependentVerifier(),
        controls=_default_control_templates(),
        notes=(
            "Read-only bootstrap fingerprint; operator confirmation is required before "
            "physical qualification.",
            "This manifest is not a qualification result.",
        ),
    )


def _default_control_templates() -> tuple[BenchControl, ...]:
    return (
        _control_template(BenchControlKind.POWER),
        _control_template(BenchControlKind.NETWORK),
        _control_template(BenchControlKind.STORAGE),
        _control_template(BenchControlKind.CLOCK),
        _control_template(BenchControlKind.RECOVERY),
    )


def _control_template(kind: BenchControlKind) -> BenchControl:
    return BenchControl(
        kind=kind,
        control_id=f"r0-{kind.value}-control",
        method=None,
        independent_observation_method=None,
        destructive_or_disruptive=True,
        operator_approval_required=True,
        bootstrap_cli_executes_action=False,
    )


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def _complete_storage_identity(device: StorageDevice) -> bool:
    return bool(
        _present(device.vendor)
        and _present(device.model)
        and _present(device.firmware)
        and device.size_bytes is not None
        and device.size_bytes > 0
    )


def _safe_id(value: str) -> str:
    rendered = _SAFE_ID_RE.sub("-", value.strip()).strip("-")
    return rendered or "host"


def _read_sysfs_text(path: str) -> str | None:
    try:
        value = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, UnicodeError):
        return None
    return value or None


def _collect_firmware() -> dict[str, str]:
    fields = {
        "bios_vendor": "/sys/class/dmi/id/bios_vendor",
        "bios_version": "/sys/class/dmi/id/bios_version",
        "bios_date": "/sys/class/dmi/id/bios_date",
        "board_name": "/sys/class/dmi/id/board_name",
        "board_vendor": "/sys/class/dmi/id/board_vendor",
        "board_version": "/sys/class/dmi/id/board_version",
    }
    result: dict[str, str] = {}
    for key, path in fields.items():
        value = _read_sysfs_text(path)
        if value:
            result[key] = value
    return result


def _cpu_model() -> str | None:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip().lower() in {
                "model name",
                "hardware",
                "processor",
            }:
                rendered = value.strip()
                if rendered and not rendered.isdigit():
                    return rendered
    except OSError:
        pass
    return platform.processor() or None


def _memory_bytes() -> int | None:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if not line.startswith("MemTotal:"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def _run_read_only(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _collect_storage() -> tuple[StorageDevice, ...]:
    raw = _run_read_only(
        [
            "lsblk",
            "-J",
            "-b",
            "-o",
            "NAME,TYPE,VENDOR,MODEL,SERIAL,REV,SIZE,TRAN",
        ]
    )
    if not raw:
        return ()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ()

    devices: list[StorageDevice] = []
    for item in payload.get("blockdevices", []):
        if not isinstance(item, dict) or item.get("type") != "disk":
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        size = item.get("size")
        try:
            size_bytes = int(size) if size is not None else None
        except (TypeError, ValueError):
            size_bytes = None
        devices.append(
            StorageDevice(
                name=name,
                vendor=_nullable_string(item.get("vendor")),
                model=_nullable_string(item.get("model")),
                serial=_nullable_string(item.get("serial")),
                firmware=_nullable_string(item.get("rev")),
                size_bytes=size_bytes,
                transport=_nullable_string(item.get("tran")),
            )
        )
    return tuple(devices)


def _collect_network() -> tuple[NetworkInterface, ...]:
    base = Path("/sys/class/net")
    if not base.exists():
        return ()
    result: list[NetworkInterface] = []
    try:
        entries = sorted(base.iterdir(), key=lambda path: path.name)
    except OSError:
        return ()
    for entry in entries:
        if entry.name == "lo":
            continue
        mac = _read_sysfs_text(str(entry / "address"))
        driver: str | None = None
        try:
            driver_link = entry / "device" / "driver"
            if driver_link.exists():
                driver = driver_link.resolve().name
        except OSError:
            driver = None
        result.append(
            NetworkInterface(
                name=entry.name,
                mac_address=mac,
                driver=driver,
                firmware=None,
            )
        )
    return tuple(result)


def _nullable_string(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _parse_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    result: dict[str, str] = {}
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        result[key.strip()] = value
    return result


def _git_revision() -> str | None:
    raw = _run_read_only(["git", "rev-parse", "HEAD"])
    if not raw:
        return None
    value = raw.strip().splitlines()[0] if raw.strip() else ""
    return value or None


def _write_manifest(path: Path, manifest: EdgeCompactR0BenchManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _render_readiness(manifest: EdgeCompactR0BenchManifest) -> dict[str, Any]:
    issues = readiness_issues(manifest)
    return {
        "manifest_id": manifest.manifest_id,
        "qualification_class": manifest.qualification_class,
        "ready_for_qualification": not issues,
        "blocking_issues": list(issues),
        "claim_boundary": "bench_readiness_only_not_a_qualification_result",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ETS Wave 1 physical Edge R0 bench bootstrap"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fingerprint_parser = subparsers.add_parser(
        "fingerprint",
        help="Collect a read-only best-effort draft fingerprint of this host",
    )
    fingerprint_parser.add_argument("--output", type=Path, required=True)
    fingerprint_parser.add_argument("--manifest-id")
    fingerprint_parser.add_argument("--asset-id")

    validate_parser = subparsers.add_parser(
        "validate-manifest",
        help="Validate a completed manifest and report physical-bench readiness",
    )
    validate_parser.add_argument("--manifest", type=Path, required=True)
    validate_parser.add_argument("--json", action="store_true", dest="as_json")

    readiness_parser = subparsers.add_parser(
        "readiness",
        help="Show readiness blockers without treating them as parser errors",
    )
    readiness_parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "fingerprint":
        manifest = fingerprint_local_linux(
            manifest_id=args.manifest_id,
            asset_id=args.asset_id,
        )
        _write_manifest(args.output, manifest)
        print(json.dumps(_render_readiness(manifest), indent=2, sort_keys=True))
        return 0

    manifest = load_manifest(args.manifest.read_bytes())
    result = _render_readiness(manifest)

    if args.command == "readiness":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "validate-manifest":
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        elif result["ready_for_qualification"]:
            print(
                f"{manifest.manifest_id}: ready for EDGE_COMPACT_R0 physical qualification"
            )
        else:
            for issue in result["blocking_issues"]:
                print(f"BLOCKED: {issue}", file=sys.stderr)
        return 0 if result["ready_for_qualification"] else 2

    raise AssertionError(f"unhandled command: {args.command}")
