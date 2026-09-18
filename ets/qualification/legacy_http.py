"""Bounded raw-artifact preservation for legacy HTTP log sources.

This module is intentionally qualification-oriented. It does not authenticate a
legacy device, infer source completeness, or turn a device log assertion into an
independent observation. Network acquisition is kept outside this module so
credentials never need to enter the retained ETS artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import ipaddress
import json
import os
import re
import urllib.parse
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SYSTEM_TCP_RE = re.compile(
    r"(?P<relative_time>\d{2}:\d{2}:\d{2})\s+TCP\s+from\s+"
    r"(?P<source_ip>\d{1,3}(?:\.\d{1,3}){3}):(?P<source_port>\d{1,5})\s+"
    r"to\s+(?P<destination_ip>\d{1,3}(?:\.\d{1,3}){3}):"
    r"(?P<destination_port>\d{1,5})"
)


class StrictLegacyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class LegacyHttpEndpointKind(StrEnum):
    OUTGOING_LOG = "outgoing_log"
    SYSTEM_LOG = "system_log"


class LegacyHttpCaptureV1(StrictLegacyModel):
    schema_version: Literal["ets.legacy-http.capture.v1"] = "ets.legacy-http.capture.v1"
    capture_id: str = Field(min_length=1, max_length=256)
    source_label: str = Field(min_length=1, max_length=256)
    source_url: str = Field(min_length=1, max_length=2048)
    endpoint_kind: LegacyHttpEndpointKind
    observer_id: str = Field(min_length=1, max_length=256)
    acquired_at_utc: datetime
    http_status: int = Field(ge=100, le=599)
    content_type: str = Field(min_length=1, max_length=256)
    raw_body_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_body_bytes: int = Field(ge=0, le=16 * 1024 * 1024)
    raw_artifact_filename: str = Field(min_length=1, max_length=255)
    source_identity_assurance: Literal["observed-network-endpoint-only"] = (
        "observed-network-endpoint-only"
    )
    source_time_quality: Literal["device-relative-or-untrusted"] = (
        "device-relative-or-untrusted"
    )
    authenticated_device_identity: Literal[False] = False
    completeness_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False
    independent_observation: Literal[False] = False

    @field_validator("acquired_at_utc")
    @classmethod
    def normalize_acquired_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("acquired_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("source_url")
    @classmethod
    def reject_credentials_in_url(cls, value: str) -> str:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source_url must not contain credentials")
        return value

    @field_validator("raw_artifact_filename")
    @classmethod
    def require_basename(cls, value: str) -> str:
        if Path(value).name != value or value in {".", ".."}:
            raise ValueError("raw_artifact_filename must be a basename")
        return value


class OutgoingLogAssertionV1(StrictLegacyModel):
    schema_version: Literal["ets.legacy-http.outgoing-log.v1"] = (
        "ets.legacy-http.outgoing-log.v1"
    )
    source_lan_ip: str
    destination: str = Field(min_length=1, max_length=1024)
    service: str = Field(min_length=1, max_length=128)
    source_time: None = None
    source_time_quality: Literal["absent"] = "absent"
    assertion_origin: Literal["legacy-device-http-log"] = "legacy-device-http-log"

    @field_validator("source_lan_ip")
    @classmethod
    def validate_source_ip(cls, value: str) -> str:
        parsed = ipaddress.ip_address(value)
        if parsed.version != 4:
            raise ValueError("source_lan_ip must be IPv4")
        return str(parsed)


class SystemTcpAssertionV1(StrictLegacyModel):
    schema_version: Literal["ets.legacy-http.system-tcp.v1"] = (
        "ets.legacy-http.system-tcp.v1"
    )
    relative_time: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")
    source_ip: str
    source_port: int = Field(ge=1, le=65535)
    destination_ip: str
    destination_port: int = Field(ge=1, le=65535)
    transport: Literal["TCP"] = "TCP"
    source_time_quality: Literal["device-relative-untrusted"] = "device-relative-untrusted"
    assertion_origin: Literal["legacy-device-http-log"] = "legacy-device-http-log"

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_ipv4(cls, value: str) -> str:
        parsed = ipaddress.ip_address(value)
        if parsed.version != 4:
            raise ValueError("system log address must be IPv4")
        return str(parsed)


class IndependentFlowObservationV1(StrictLegacyModel):
    observer_id: str = Field(min_length=1, max_length=256)
    observed_at_utc: datetime
    transport: Literal["TCP", "UDP", "ICMP"]
    source_ip: str
    source_port: int | None = Field(default=None, ge=1, le=65535)
    destination_ip: str
    destination_port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_flow_ip(cls, value: str) -> str:
        parsed = ipaddress.ip_address(value)
        if parsed.version != 4:
            raise ValueError("flow address must be IPv4")
        return str(parsed)


class LegacyHttpCorrelationV1(StrictLegacyModel):
    schema_version: Literal["ets.legacy-http.correlation.v1"] = (
        "ets.legacy-http.correlation.v1"
    )
    matched: bool
    matched_fields: tuple[str, ...]
    assertion_origin: Literal["legacy-device-http-log"] = "legacy-device-http-log"
    independent_observer_id: str = Field(min_length=1, max_length=256)
    corroborates_device_assertion: bool
    authenticated_device_identity: Literal[False] = False
    completeness_proven: Literal[False] = False
    semantic_truth_proven: Literal[False] = False


class _TableParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[str, ...]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._row is not None and self._cell is not None:
            value = " ".join("".join(self._cell).split())
            self._row.append(value)
            self._cell = None
        elif lowered == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(tuple(self._row))
            self._row = None
            self._cell = None


class _VisibleTextParser(html.parser.HTMLParser):
    _BREAK_TAGS = frozenset({"br", "p", "div", "tr", "li", "pre", "textarea"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.lower() in self._BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def build_capture(
    raw_body: bytes,
    *,
    source_label: str,
    source_url: str,
    endpoint_kind: LegacyHttpEndpointKind,
    observer_id: str,
    acquired_at_utc: datetime,
    http_status: int = 200,
    content_type: str = "text/html",
) -> LegacyHttpCaptureV1:
    digest = hashlib.sha256(raw_body).hexdigest()
    artifact_filename = f"{endpoint_kind.value}-{digest[:24]}.http-body.bin"
    capture_id = f"legacy-http-{endpoint_kind.value}-{digest[:24]}"
    return LegacyHttpCaptureV1(
        capture_id=capture_id,
        source_label=source_label,
        source_url=source_url,
        endpoint_kind=endpoint_kind,
        observer_id=observer_id,
        acquired_at_utc=acquired_at_utc,
        http_status=http_status,
        content_type=content_type,
        raw_body_sha256=digest,
        raw_body_bytes=len(raw_body),
        raw_artifact_filename=artifact_filename,
    )


def preserve_capture(
    raw_body: bytes,
    capture: LegacyHttpCaptureV1,
    output_dir: Path,
) -> tuple[Path, Path]:
    if not verify_capture(raw_body, capture):
        raise ValueError("raw body does not match capture digest/length")
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)

    raw_path = output_dir / capture.raw_artifact_filename
    metadata_path = output_dir / f"{capture.capture_id}.json"
    raw_path.write_bytes(raw_body)
    os.chmod(raw_path, 0o600)
    metadata_path.write_text(
        json.dumps(capture.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(metadata_path, 0o600)
    return raw_path, metadata_path


def verify_capture(raw_body: bytes, capture: LegacyHttpCaptureV1) -> bool:
    return (
        len(raw_body) == capture.raw_body_bytes
        and hashlib.sha256(raw_body).hexdigest() == capture.raw_body_sha256
    )


def parse_outgoing_log(raw_body: bytes) -> tuple[OutgoingLogAssertionV1, ...]:
    parser = _TableParser()
    parser.feed(raw_body.decode("latin-1"))
    assertions: list[OutgoingLogAssertionV1] = []
    for row in parser.rows:
        if len(row) < 3:
            continue
        source, destination, service = row[:3]
        if source.casefold() == "lan ip":
            continue
        try:
            ipaddress.IPv4Address(source)
        except ipaddress.AddressValueError:
            continue
        if not destination or not service:
            continue
        assertions.append(
            OutgoingLogAssertionV1(
                source_lan_ip=source,
                destination=destination,
                service=service,
            )
        )
    return tuple(assertions)


def parse_system_tcp_log(raw_body: bytes) -> tuple[SystemTcpAssertionV1, ...]:
    parser = _VisibleTextParser()
    parser.feed(raw_body.decode("latin-1"))
    text = "".join(parser.parts)
    assertions: list[SystemTcpAssertionV1] = []
    for match in _SYSTEM_TCP_RE.finditer(text):
        source_ip = match.group("source_ip")
        destination_ip = match.group("destination_ip")
        try:
            ipaddress.IPv4Address(source_ip)
            ipaddress.IPv4Address(destination_ip)
        except ipaddress.AddressValueError:
            continue
        source_port = int(match.group("source_port"))
        destination_port = int(match.group("destination_port"))
        if not (1 <= source_port <= 65535 and 1 <= destination_port <= 65535):
            continue
        assertions.append(
            SystemTcpAssertionV1(
                relative_time=match.group("relative_time"),
                source_ip=source_ip,
                source_port=source_port,
                destination_ip=destination_ip,
                destination_port=destination_port,
            )
        )
    return tuple(assertions)


def correlate_outgoing_assertion(
    assertion: OutgoingLogAssertionV1,
    observation: IndependentFlowObservationV1,
) -> LegacyHttpCorrelationV1:
    matched_fields: list[str] = []
    if assertion.source_lan_ip == observation.source_ip:
        matched_fields.append("source_ip")
    if assertion.destination == observation.destination_ip:
        matched_fields.append("destination_ip")
    service_match = _service_matches_flow(assertion.service, observation)
    if service_match:
        matched_fields.append("service_or_port")
    matched = len(matched_fields) == 3
    return LegacyHttpCorrelationV1(
        matched=matched,
        matched_fields=tuple(matched_fields),
        independent_observer_id=observation.observer_id,
        corroborates_device_assertion=matched,
    )


def correlate_system_tcp_assertion(
    assertion: SystemTcpAssertionV1,
    observation: IndependentFlowObservationV1,
) -> LegacyHttpCorrelationV1:
    checks = {
        "transport": observation.transport == "TCP",
        "source_ip": assertion.source_ip == observation.source_ip,
        "source_port": assertion.source_port == observation.source_port,
        "destination_ip": assertion.destination_ip == observation.destination_ip,
        "destination_port": assertion.destination_port == observation.destination_port,
    }
    matched_fields = tuple(name for name, matched in checks.items() if matched)
    matched = all(checks.values())
    return LegacyHttpCorrelationV1(
        matched=matched,
        matched_fields=matched_fields,
        independent_observer_id=observation.observer_id,
        corroborates_device_assertion=matched,
    )


def _service_matches_flow(
    service: str,
    observation: IndependentFlowObservationV1,
) -> bool:
    normalized = service.strip().casefold()
    if normalized == "http":
        return observation.transport == "TCP" and observation.destination_port == 80
    if normalized == "https":
        return observation.transport == "TCP" and observation.destination_port == 443
    if normalized.isdigit():
        return observation.destination_port == int(normalized)
    return False


def _capture_command(args: argparse.Namespace) -> int:
    raw_body = Path(args.input).read_bytes() if args.input != "-" else os.read(0, 16 * 1024 * 1024)
    acquired_at = datetime.now(tz=UTC)
    capture = build_capture(
        raw_body,
        source_label=args.source_label,
        source_url=args.source_url,
        endpoint_kind=LegacyHttpEndpointKind(args.endpoint_kind),
        observer_id=args.observer_id,
        acquired_at_utc=acquired_at,
        http_status=args.http_status,
        content_type=args.content_type,
    )
    raw_path, metadata_path = preserve_capture(raw_body, capture, Path(args.output_dir))
    if capture.endpoint_kind == LegacyHttpEndpointKind.OUTGOING_LOG:
        parsed: tuple[StrictLegacyModel, ...] = parse_outgoing_log(raw_body)
    else:
        parsed = parse_system_tcp_log(raw_body)
    normalized_path = Path(args.output_dir) / f"{capture.capture_id}.normalized.json"
    normalized_path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in parsed],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(normalized_path, 0o600)
    print(
        json.dumps(
            {
                "capture_id": capture.capture_id,
                "raw_artifact": str(raw_path),
                "metadata": str(metadata_path),
                "normalized": str(normalized_path),
                "raw_body_sha256": capture.raw_body_sha256,
                "parsed_records": len(parsed),
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    capture = LegacyHttpCaptureV1.model_validate_json(Path(args.metadata).read_text("utf-8"))
    raw_body = Path(args.raw).read_bytes()
    valid = verify_capture(raw_body, capture)
    print(json.dumps({"capture_id": capture.capture_id, "valid": valid}, sort_keys=True))
    return 0 if valid else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preserve and parse bounded legacy HTTP log artifacts"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument(
        "--input",
        required=True,
        help="raw HTTP body file or '-' for stdin",
    )
    capture_parser.add_argument("--output-dir", required=True)
    capture_parser.add_argument("--source-label", required=True)
    capture_parser.add_argument("--source-url", required=True)
    capture_parser.add_argument(
        "--endpoint-kind",
        required=True,
        choices=[item.value for item in LegacyHttpEndpointKind],
    )
    capture_parser.add_argument("--observer-id", required=True)
    capture_parser.add_argument("--http-status", type=int, default=200)
    capture_parser.add_argument("--content-type", default="text/html")
    capture_parser.set_defaults(func=_capture_command)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--metadata", required=True)
    verify_parser.add_argument("--raw", required=True)
    verify_parser.set_defaults(func=_verify_command)

    args = parser.parse_args(argv)
    func = args.func
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
