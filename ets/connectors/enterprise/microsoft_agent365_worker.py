"""Hosted Agent 365 acquisition worker and protected source-payload reference store."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
)
from ets.connectors.credentials.models import (
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialReferenceV1,
)
from ets.connectors.credentials.provider import CredentialProvider
from ets.connectors.enterprise.microsoft_agent365 import (
    Agent365SourceType,
    MicrosoftSourceEnvelopeV1,
    build_source_envelope,
)
from ets.connectors.enterprise.microsoft_agent365_custody import (
    MicrosoftAgent365CustodyStore,
    MicrosoftAgent365SnapshotCheckpointV1,
)
from ets.connectors.enterprise.microsoft_agent365_http import (
    MicrosoftAgent365DetailAcquisition,
    MicrosoftAgent365HttpClient,
    MicrosoftAgent365InventoryAcquisition,
    MicrosoftAgent365InventorySnapshot,
    MicrosoftAgent365LiveCollector,
)

_PROTECTED_REFERENCE_SCHEME: Final = "ets-protected"
_PROTECTED_REFERENCE_HOST: Final = "agent365"
_PROTECTED_FILE_MAGIC: Final = b"ETSA365P1"
_AES_GCM_NONCE_BYTES: Final = 12
_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

Clock = Callable[[], datetime]
HttpClientFactory = Callable[[bytes], MicrosoftAgent365HttpClient]


class MicrosoftAgent365WorkerError(RuntimeError):
    """Base error for the bounded hosted Agent 365 worker."""


class MicrosoftAgent365ProtectedPayloadError(MicrosoftAgent365WorkerError):
    """Raised when protected source-payload storage cannot preserve its contract."""


class MicrosoftAgent365ProtectedPayloadConflict(MicrosoftAgent365ProtectedPayloadError):
    """Raised when one durable acquisition coordinate resolves to different source bytes."""


class MicrosoftAgent365ProtectedPayloadIntegrityError(MicrosoftAgent365ProtectedPayloadError):
    """Raised when protected payload bytes fail authenticated decryption or digest verification."""


@dataclass(frozen=True, slots=True)
class _ProtectedReference:
    tenant_id: str
    acquisition_sequence: int
    source_type: Agent365SourceType
    raw_payload_sha256: str


class MicrosoftAgent365EncryptedPayloadStore:
    """AES-GCM software reference store for exact Agent 365 source bytes.

    The encryption key is runtime material supplied by the hosted environment. This reference
    implementation does not claim HSM, immutable-object, or ETS Vault custody semantics.
    """

    def __init__(self, root: Path, encryption_key: bytes) -> None:
        if len(encryption_key) != 32:
            raise ValueError("Agent 365 protected-payload key must be 32 bytes")
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._key = bytearray(encryption_key)
        self._closed = False

    def __repr__(self) -> str:
        return f"MicrosoftAgent365EncryptedPayloadStore(root={self._root!s}, key=<redacted>)"

    def put_exact_source(
        self,
        payload: bytes,
        *,
        tenant_id: str,
        acquisition_sequence: int,
        source_type: Agent365SourceType,
    ) -> str:
        """Encrypt exact source bytes and return an opaque deterministic custody reference."""

        self._ensure_open()
        if not payload:
            raise MicrosoftAgent365ProtectedPayloadError("protected Agent 365 payload is empty")
        normalized_tenant = _normalize_tenant_id(tenant_id)
        if acquisition_sequence < 0:
            raise ValueError("acquisition_sequence must be non-negative")
        digest = hashlib.sha256(payload).hexdigest()
        reference = _build_protected_reference(
            tenant_id=normalized_tenant,
            acquisition_sequence=acquisition_sequence,
            source_type=source_type,
            raw_payload_sha256=digest,
        )
        final_path = self._payload_path(
            tenant_id=normalized_tenant,
            acquisition_sequence=acquisition_sequence,
            source_type=source_type,
            raw_payload_sha256=digest,
        )
        final_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        if final_path.exists():
            existing = self.read_exact_source(reference)
            if existing != payload:
                raise MicrosoftAgent365ProtectedPayloadConflict(
                    "protected Agent 365 acquisition coordinate already contains different bytes"
                )
            return reference

        nonce = os.urandom(_AES_GCM_NONCE_BYTES)
        aad = _protected_aad(
            tenant_id=normalized_tenant,
            acquisition_sequence=acquisition_sequence,
            source_type=source_type,
            raw_payload_sha256=digest,
        )
        ciphertext = AESGCM(bytes(self._key)).encrypt(nonce, payload, aad)
        encoded = _PROTECTED_FILE_MAGIC + nonce + ciphertext
        temporary_path = final_path.with_name(f".{final_path.name}.{uuid4().hex}.tmp")
        try:
            descriptor = os.open(
                temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            if final_path.exists():
                existing = self.read_exact_source(reference)
                if existing != payload:
                    raise MicrosoftAgent365ProtectedPayloadConflict(
                        "protected Agent 365 acquisition coordinate raced with different bytes"
                    )
                temporary_path.unlink(missing_ok=True)
                return reference
            os.replace(temporary_path, final_path)
            _fsync_directory(final_path.parent)
        finally:
            temporary_path.unlink(missing_ok=True)
        return reference

    def read_exact_source(self, reference: str) -> bytes:
        """Decrypt and verify exact source bytes for qualification and later replay."""

        self._ensure_open()
        parsed = _parse_protected_reference(reference)
        path = self._payload_path(
            tenant_id=parsed.tenant_id,
            acquisition_sequence=parsed.acquisition_sequence,
            source_type=parsed.source_type,
            raw_payload_sha256=parsed.raw_payload_sha256,
        )
        try:
            encoded = path.read_bytes()
        except OSError as exc:
            raise MicrosoftAgent365ProtectedPayloadError(
                "protected Agent 365 payload is unavailable"
            ) from exc
        minimum_size = len(_PROTECTED_FILE_MAGIC) + _AES_GCM_NONCE_BYTES + 16
        if len(encoded) < minimum_size or not encoded.startswith(_PROTECTED_FILE_MAGIC):
            raise MicrosoftAgent365ProtectedPayloadIntegrityError(
                "protected Agent 365 payload framing is invalid"
            )
        offset = len(_PROTECTED_FILE_MAGIC)
        nonce = encoded[offset : offset + _AES_GCM_NONCE_BYTES]
        ciphertext = encoded[offset + _AES_GCM_NONCE_BYTES :]
        aad = _protected_aad(
            tenant_id=parsed.tenant_id,
            acquisition_sequence=parsed.acquisition_sequence,
            source_type=parsed.source_type,
            raw_payload_sha256=parsed.raw_payload_sha256,
        )
        try:
            payload = AESGCM(bytes(self._key)).decrypt(nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise MicrosoftAgent365ProtectedPayloadIntegrityError(
                "protected Agent 365 payload authentication failed"
            ) from exc
        if hashlib.sha256(payload).hexdigest() != parsed.raw_payload_sha256:
            raise MicrosoftAgent365ProtectedPayloadIntegrityError(
                "protected Agent 365 payload digest does not match its custody reference"
            )
        return payload

    def close(self) -> None:
        if self._closed:
            return
        for index in range(len(self._key)):
            self._key[index] = 0
        self._closed = True

    def __enter__(self) -> MicrosoftAgent365EncryptedPayloadStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _payload_path(
        self,
        *,
        tenant_id: str,
        acquisition_sequence: int,
        source_type: Agent365SourceType,
        raw_payload_sha256: str,
    ) -> Path:
        source_segment = _source_segment(source_type)
        return (
            self._root
            / tenant_id
            / f"{acquisition_sequence:020d}"
            / source_segment
            / f"{raw_payload_sha256}.a365"
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise MicrosoftAgent365ProtectedPayloadError(
                "Agent 365 protected-payload store is closed"
            )


class MicrosoftAgent365HostedWorker:
    """One-shot schedulable Agent 365 worker using Gateway-owned Graph identity."""

    def __init__(
        self,
        *,
        credential_provider: CredentialProvider,
        custody_store: MicrosoftAgent365CustodyStore,
        protected_payload_store: MicrosoftAgent365EncryptedPayloadStore,
        tenant_id: str,
        collector_identity: str,
        collector_version: str,
        clock: Clock | None = None,
        http_client_factory: HttpClientFactory = MicrosoftAgent365HttpClient,
    ) -> None:
        self._credential_provider = credential_provider
        self._custody_store = custody_store
        self._protected_payload_store = protected_payload_store
        self._tenant_id = _normalize_tenant_id(tenant_id)
        if not collector_identity.strip():
            raise ValueError("collector_identity is required")
        if not collector_version.strip():
            raise ValueError("collector_version is required")
        self._collector_identity = collector_identity
        self._collector_version = collector_version
        self._clock = clock or _utc_now
        self._http_client_factory = http_client_factory

    def run_once(
        self,
        *,
        include_details: bool = True,
        maximum_pages: int = 100,
        maximum_packages: int = 10_000,
    ) -> MicrosoftAgent365SnapshotCheckpointV1:
        """Acquire, externalize, re-chain, and durably commit one bounded inventory snapshot."""

        previous_checkpoint = self._custody_store.get_latest_checkpoint(self._tenant_id)
        starting_sequence = (
            0
            if previous_checkpoint is None
            else previous_checkpoint.last_acquisition_sequence + 1
        )
        previous_envelope_hash = (
            None if previous_checkpoint is None else previous_checkpoint.last_envelope_hash
        )
        reference = CredentialReferenceV1(
            schema_version=CREDENTIAL_REFERENCE_SCHEMA_VERSION,
            ref=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        )
        with self._credential_provider.resolve(reference) as lease:
            client = self._http_client_factory(lease.reveal())
            try:
                collector = MicrosoftAgent365LiveCollector(
                    client,
                    tenant_id=self._tenant_id,
                    collector_identity=self._collector_identity,
                    collector_version=self._collector_version,
                    payload_retention="digest_only",
                    clock=self._clock,
                )
                transient_snapshot = collector.collect_snapshot(
                    include_details=include_details,
                    maximum_pages=maximum_pages,
                    maximum_packages=maximum_packages,
                )
            finally:
                client.close()

        protected_snapshot = _protect_and_rechain_snapshot(
            transient_snapshot,
            protected_payload_store=self._protected_payload_store,
            tenant_id=self._tenant_id,
            starting_sequence=starting_sequence,
            previous_envelope_hash=previous_envelope_hash,
        )
        return self._custody_store.commit_snapshot(
            protected_snapshot,
            completed_at_utc=self._normalized_now(),
        )

    def _normalized_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise MicrosoftAgent365WorkerError("Agent 365 worker clock must be timezone-aware")
        return value.astimezone(UTC)


def _protect_and_rechain_snapshot(
    snapshot: MicrosoftAgent365InventorySnapshot,
    *,
    protected_payload_store: MicrosoftAgent365EncryptedPayloadStore,
    tenant_id: str,
    starting_sequence: int,
    previous_envelope_hash: str | None,
) -> MicrosoftAgent365InventorySnapshot:
    sequence = starting_sequence
    previous_hash = previous_envelope_hash
    protected_pages: list[MicrosoftAgent365InventoryAcquisition] = []
    protected_details: list[MicrosoftAgent365DetailAcquisition] = []

    for acquisition in snapshot.inventory_pages:
        envelope = _protect_and_rechain_envelope(
            acquisition.envelope,
            acquisition.response.body,
            expected_source_type="agent365.package_inventory",
            protected_payload_store=protected_payload_store,
            tenant_id=tenant_id,
            acquisition_sequence=sequence,
            previous_envelope_hash=previous_hash,
        )
        protected_pages.append(
            MicrosoftAgent365InventoryAcquisition(
                response=acquisition.response,
                envelope=envelope,
                page=acquisition.page,
            )
        )
        sequence += 1
        previous_hash = envelope.envelope_hash

    for acquisition in snapshot.package_details:
        envelope = _protect_and_rechain_envelope(
            acquisition.envelope,
            acquisition.response.body,
            expected_source_type="agent365.package_detail",
            protected_payload_store=protected_payload_store,
            tenant_id=tenant_id,
            acquisition_sequence=sequence,
            previous_envelope_hash=previous_hash,
        )
        protected_details.append(
            MicrosoftAgent365DetailAcquisition(
                response=acquisition.response,
                envelope=envelope,
                detail=acquisition.detail,
            )
        )
        sequence += 1
        previous_hash = envelope.envelope_hash

    return MicrosoftAgent365InventorySnapshot(
        inventory_pages=tuple(protected_pages),
        package_details=tuple(protected_details),
    )


def _protect_and_rechain_envelope(
    source: MicrosoftSourceEnvelopeV1,
    payload: bytes,
    *,
    expected_source_type: Agent365SourceType,
    protected_payload_store: MicrosoftAgent365EncryptedPayloadStore,
    tenant_id: str,
    acquisition_sequence: int,
    previous_envelope_hash: str | None,
) -> MicrosoftSourceEnvelopeV1:
    if source.tenant_id != tenant_id:
        raise MicrosoftAgent365WorkerError("transient Agent 365 snapshot tenant drifted")
    if source.source_type != expected_source_type:
        raise MicrosoftAgent365WorkerError("transient Agent 365 snapshot source type drifted")
    reference = protected_payload_store.put_exact_source(
        payload,
        tenant_id=tenant_id,
        acquisition_sequence=acquisition_sequence,
        source_type=expected_source_type,
    )
    return build_source_envelope(
        payload,
        source_type=expected_source_type,
        tenant_id=tenant_id,
        acquisition_time=source.acquisition_time,
        microsoft_event_time=source.microsoft_event_time,
        api_version=source.api_version,
        api_maturity=source.api_maturity,
        request_path=source.request_path,
        collector_identity=source.collector_identity,
        collector_version=source.collector_version,
        acquisition_sequence=acquisition_sequence,
        previous_envelope_hash=previous_envelope_hash,
        payload_retention="protected_reference",
        protected_payload_reference=reference,
    )


def _build_protected_reference(
    *,
    tenant_id: str,
    acquisition_sequence: int,
    source_type: Agent365SourceType,
    raw_payload_sha256: str,
) -> str:
    return (
        f"{_PROTECTED_REFERENCE_SCHEME}://{_PROTECTED_REFERENCE_HOST}/"
        f"{tenant_id}/{acquisition_sequence}/{_source_segment(source_type)}/{raw_payload_sha256}"
    )


def _parse_protected_reference(reference: str) -> _ProtectedReference:
    parsed = urlsplit(reference)
    if (
        parsed.scheme != _PROTECTED_REFERENCE_SCHEME
        or parsed.hostname != _PROTECTED_REFERENCE_HOST
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MicrosoftAgent365ProtectedPayloadIntegrityError(
            "protected Agent 365 payload reference escaped its qualified namespace"
        )
    segments = parsed.path.strip("/").split("/")
    if len(segments) != 4:
        raise MicrosoftAgent365ProtectedPayloadIntegrityError(
            "protected Agent 365 payload reference has an invalid shape"
        )
    tenant_id = _normalize_tenant_id(segments[0])
    try:
        acquisition_sequence = int(segments[1])
    except ValueError as exc:
        raise MicrosoftAgent365ProtectedPayloadIntegrityError(
            "protected Agent 365 payload sequence is invalid"
        ) from exc
    if acquisition_sequence < 0 or str(acquisition_sequence) != segments[1]:
        raise MicrosoftAgent365ProtectedPayloadIntegrityError(
            "protected Agent 365 payload sequence is not canonical"
        )
    source_type = _source_type(segments[2])
    digest = segments[3]
    if _SHA256_PATTERN.fullmatch(digest) is None:
        raise MicrosoftAgent365ProtectedPayloadIntegrityError(
            "protected Agent 365 payload digest is invalid"
        )
    return _ProtectedReference(
        tenant_id=tenant_id,
        acquisition_sequence=acquisition_sequence,
        source_type=source_type,
        raw_payload_sha256=digest,
    )


def _protected_aad(
    *,
    tenant_id: str,
    acquisition_sequence: int,
    source_type: Agent365SourceType,
    raw_payload_sha256: str,
) -> bytes:
    return json.dumps(
        {
            "schema_version": "ets.connector.microsoft.agent365.protected_payload.v1",
            "tenant_id": tenant_id,
            "acquisition_sequence": acquisition_sequence,
            "source_type": source_type,
            "raw_payload_sha256": raw_payload_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _source_segment(source_type: Agent365SourceType) -> str:
    if source_type == "agent365.package_inventory":
        return "inventory"
    if source_type == "agent365.package_detail":
        return "detail"
    raise ValueError("unsupported Agent 365 source type")


def _source_type(segment: str) -> Agent365SourceType:
    if segment == "inventory":
        return "agent365.package_inventory"
    if segment == "detail":
        return "agent365.package_detail"
    raise MicrosoftAgent365ProtectedPayloadIntegrityError(
        "protected Agent 365 payload source type is invalid"
    )


def _normalize_tenant_id(value: str) -> str:
    if _GUID_PATTERN.fullmatch(value) is None:
        raise ValueError("Agent 365 tenant_id must be a canonical GUID string")
    return value.lower()


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _utc_now() -> datetime:
    return datetime.now(UTC)
