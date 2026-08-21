"""Online and offline verifier orchestration for ETS proof bundles.

The legacy verifier helpers remain intentionally small and backwards compatible.
This module adds the stricter trust, signature, leaf-binding, and live continuity
checks required for production-style verification.
"""

from __future__ import annotations

import json
import ssl
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from typing import Any, Literal, Protocol, Self, cast
from urllib.parse import quote, urlencode, urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ets.core import ConsistencyProof, EvidenceProofBundle, SignedTreeHead, canonical_sha256
from ets.core.merkle import leaf_hash_for_event_hash
from ets.core.proofs import verify_consistency_proof, verify_inclusion_proof
from ets.core.signing import verify_tree_head_signature

VerifierMode = Literal["offline", "online"]
StandingStatus = Literal["checkpoint_only", "current_log"]
SignatureAlgorithm = Literal["ed25519", "ps256"]


class VerificationTransportError(RuntimeError):
    """Raised when an online verifier cannot safely retrieve verifier material."""


class VerificationCheck(BaseModel):
    """One fail-closed verifier check and its human-readable result."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: str = Field(min_length=1)
    passed: bool
    reason: str = Field(min_length=1)


class TrustedTreeHeadKey(BaseModel):
    """Out-of-band trust material for an ETS tree-head signing key."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    key_id: str = Field(min_length=1)
    signature_alg: SignatureAlgorithm
    public_key_hex: str = Field(min_length=2)
    not_before_utc: datetime | None = None
    not_after_utc: datetime | None = None
    revoked_at_utc: datetime | None = None

    @field_validator("public_key_hex")
    @classmethod
    def require_public_key_hex(cls, value: str) -> str:
        bytes.fromhex(value)
        return value

    @field_validator("not_before_utc", "not_after_utc", "revoked_at_utc")
    @classmethod
    def require_utc_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trust key timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_key_contract(self) -> Self:
        if self.signature_alg == "ed25519" and len(self.public_key_hex) != 64:
            raise ValueError("Ed25519 public keys must be 32 bytes encoded as 64 hex characters")
        if (
            self.not_before_utc is not None
            and self.not_after_utc is not None
            and self.not_after_utc < self.not_before_utc
        ):
            raise ValueError("trust key not_after_utc must not precede not_before_utc")
        return self


class TreeHeadTrustStore(BaseModel):
    """Verifier-owned trust store; it is never accepted from an evidence bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["ets.verifier_trust.v1"] = "ets.verifier_trust.v1"
    keys: list[TrustedTreeHeadKey] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_key_ids(self) -> Self:
        key_ids = [key.key_id for key in self.keys]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("trust store key_id values must be unique")
        return self

    def get(self, key_id: str) -> TrustedTreeHeadKey | None:
        for key in self.keys:
            if key.key_id == key_id:
                return key
        return None


class VerifierPolicy(BaseModel):
    """Fail-closed policy controls shared by online and offline verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    require_tree_head_signature: bool = True
    expected_log_id: str | None = None
    max_future_skew_seconds: int = Field(default=300, ge=0, le=3600)


class VerifierOutcome(BaseModel):
    """Normalized result returned by both verifier modes."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    valid: bool
    mode: VerifierMode
    reason: str
    event_id: str
    log_id: str
    event_hash: str
    leaf_hash: str
    checkpoint_root_hash: str
    checkpoint_tree_size: int = Field(ge=1)
    latest_root_hash: str | None = None
    latest_tree_size: int | None = Field(default=None, ge=0)
    signature_verified: bool
    continuity_verified: bool
    standing_status: StandingStatus
    checks: list[VerificationCheck]
    verified_at_utc: datetime


class JSONTransport(Protocol):
    """Minimal injectable transport used by the online verifier."""

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> Mapping[str, Any]:
        """Return a JSON object from a URL or raise VerificationTransportError."""


class StdlibJSONTransport:
    """TLS-validating, no-redirect JSON transport with bounded response reads."""

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> Mapping[str, Any]:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host is None or parsed.scheme not in {"https", "http"}:
            raise VerificationTransportError("verifier URL must use HTTP or HTTPS with a host")

        connection: HTTPConnection
        if parsed.scheme == "https":
            connection = HTTPSConnection(
                host,
                port=parsed.port,
                timeout=timeout_seconds,
                context=ssl.create_default_context(),
            )
        else:
            connection = HTTPConnection(host, port=parsed.port, timeout=timeout_seconds)

        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"

        try:
            connection.request("GET", target, headers=dict(headers))
            response = connection.getresponse()
            if response.status != 200:
                response.read(min(max_response_bytes, 4096))
                raise VerificationTransportError(
                    f"verifier endpoint returned HTTP {response.status}"
                )
            content_type = (response.getheader("Content-Type") or "").lower()
            if content_type and "json" not in content_type:
                raise VerificationTransportError("verifier endpoint did not return JSON")
            body = response.read(max_response_bytes + 1)
        except (HTTPException, OSError, TimeoutError) as exc:
            raise VerificationTransportError("verifier endpoint request failed") from exc
        finally:
            connection.close()

        if len(body) > max_response_bytes:
            raise VerificationTransportError("verifier endpoint response exceeds configured limit")

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VerificationTransportError("verifier endpoint returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise VerificationTransportError("verifier endpoint JSON must be an object")
        return cast(Mapping[str, Any], payload)


def verify_offline_bundle(
    bundle: EvidenceProofBundle | Mapping[str, Any],
    *,
    trust_store: TreeHeadTrustStore | None = None,
    policy: VerifierPolicy | None = None,
    verified_at_utc: datetime | None = None,
) -> VerifierOutcome:
    """Verify a downloaded ETS bundle without making any network requests.

    Offline verification proves integrity and inclusion at the signed checkpoint.
    It intentionally does not claim that the checkpoint is the current log state.
    """

    parsed_bundle = _parse_bundle(bundle)
    effective_policy = policy or VerifierPolicy()
    effective_trust_store = trust_store or TreeHeadTrustStore()
    verified_at = _normalize_verification_time(verified_at_utc)
    checks: list[VerificationCheck] = []

    event_hash = canonical_sha256(parsed_bundle.event.hashable_payload())
    _record(
        checks,
        "event_hash",
        event_hash == parsed_bundle.event_hash,
        "event hash matches canonical event" if event_hash == parsed_bundle.event_hash else
        "bundle event hash does not match canonical event",
    )

    expected_leaf_hash = leaf_hash_for_event_hash(event_hash)
    _record(
        checks,
        "leaf_binding",
        expected_leaf_hash == parsed_bundle.leaf_hash,
        "leaf hash is bound to event hash" if expected_leaf_hash == parsed_bundle.leaf_hash else
        "bundle leaf hash is not derived from the canonical event hash",
    )
    _record(
        checks,
        "proof_leaf_binding",
        parsed_bundle.inclusion_proof.leaf_hash == parsed_bundle.leaf_hash,
        "proof leaf matches bundle leaf" if
        parsed_bundle.inclusion_proof.leaf_hash == parsed_bundle.leaf_hash else
        "inclusion proof leaf does not match bundle leaf",
    )

    proof_result = verify_inclusion_proof(parsed_bundle.inclusion_proof)
    _record(checks, "inclusion_proof", proof_result.valid, proof_result.reason)

    root_matches = parsed_bundle.tree_head.root_hash == parsed_bundle.inclusion_proof.root_hash
    _record(
        checks,
        "checkpoint_root_binding",
        root_matches,
        "tree head root matches inclusion proof" if root_matches else
        "tree head root does not match inclusion proof root",
    )
    size_matches = parsed_bundle.tree_head.tree_size == parsed_bundle.inclusion_proof.tree_size
    _record(
        checks,
        "checkpoint_size_binding",
        size_matches,
        "tree head size matches inclusion proof" if size_matches else
        "tree head size does not match inclusion proof size",
    )

    expected_log_matches = (
        effective_policy.expected_log_id is None
        or parsed_bundle.tree_head.log_id == effective_policy.expected_log_id
    )
    _record(
        checks,
        "log_identity",
        expected_log_matches,
        "log identity accepted" if expected_log_matches else "tree head log_id is not trusted",
    )

    future_limit = verified_at + timedelta(seconds=effective_policy.max_future_skew_seconds)
    checkpoint_time_ok = parsed_bundle.tree_head.created_at_utc <= future_limit
    _record(
        checks,
        "checkpoint_time",
        checkpoint_time_ok,
        "checkpoint time is plausible" if checkpoint_time_ok else
        "checkpoint timestamp is too far in the future",
    )

    signature_verified, signature_reason = _verify_tree_head_trust(
        parsed_bundle.tree_head,
        effective_trust_store,
    )
    if effective_policy.require_tree_head_signature:
        _record(checks, "tree_head_signature", signature_verified, signature_reason)
    elif _has_any_signature_field(parsed_bundle.tree_head):
        _record(checks, "tree_head_signature", signature_verified, signature_reason)
    else:
        _record(
            checks,
            "tree_head_signature",
            True,
            "unsigned checkpoint accepted only because policy explicitly allows it",
        )

    return _outcome(
        mode="offline",
        bundle=parsed_bundle,
        checks=checks,
        verified_at_utc=verified_at,
        signature_verified=signature_verified,
        continuity_verified=False,
        standing_status="checkpoint_only",
    )


def verify_online_event(
    base_url: str,
    event_id: str,
    *,
    trust_store: TreeHeadTrustStore | None = None,
    policy: VerifierPolicy | None = None,
    transport: JSONTransport | None = None,
    headers: Mapping[str, str] | None = None,
    allowed_hosts: tuple[str, ...] = (),
    allow_insecure_http: bool = False,
    timeout_seconds: float = 5.0,
    max_response_bytes: int = 2 * 1024 * 1024,
    verified_at_utc: datetime | None = None,
) -> VerifierOutcome:
    """Verify an ETS event against a live log and prove append-only continuity."""

    if not event_id:
        raise ValueError("event_id is required")
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValueError("timeout_seconds must be greater than zero and at most 60")
    if max_response_bytes < 1024 or max_response_bytes > 16 * 1024 * 1024:
        raise ValueError("max_response_bytes must be between 1 KiB and 16 MiB")

    endpoint = _validated_base_url(
        base_url,
        allowed_hosts=allowed_hosts,
        allow_insecure_http=allow_insecure_http,
    )
    effective_transport = transport or StdlibJSONTransport()
    effective_headers = headers or {}
    effective_policy = policy or VerifierPolicy()
    effective_trust_store = trust_store or TreeHeadTrustStore()
    verified_at = _normalize_verification_time(verified_at_utc)

    bundle_url = f"{endpoint}/api/v1/bundles/{quote(event_id, safe='')}"
    bundle_payload = effective_transport.get_json(
        bundle_url,
        headers=effective_headers,
        timeout_seconds=timeout_seconds,
        max_response_bytes=max_response_bytes,
    )
    parsed_bundle = _parse_bundle(bundle_payload)
    if parsed_bundle.event.event_id != event_id:
        offline = verify_offline_bundle(
            parsed_bundle,
            trust_store=effective_trust_store,
            policy=effective_policy,
            verified_at_utc=verified_at,
        )
        mismatch = VerificationCheck(
            code="requested_event",
            passed=False,
            reason="server bundle event_id does not match requested event_id",
        )
        return offline.model_copy(
            update={
                "mode": "online",
                "valid": False,
                "reason": mismatch.reason,
                "checks": [*offline.checks, mismatch],
            }
        )

    offline = verify_offline_bundle(
        parsed_bundle,
        trust_store=effective_trust_store,
        policy=effective_policy,
        verified_at_utc=verified_at,
    )
    if not offline.valid:
        return offline.model_copy(update={"mode": "online"})

    checks = list(offline.checks)
    latest_payload = effective_transport.get_json(
        f"{endpoint}/api/v1/log/head",
        headers=effective_headers,
        timeout_seconds=timeout_seconds,
        max_response_bytes=max_response_bytes,
    )
    latest_head = _parse_tree_head(latest_payload)

    log_matches = latest_head.log_id == parsed_bundle.tree_head.log_id
    _record(
        checks,
        "latest_log_identity",
        log_matches,
        "latest head uses the same log identity" if log_matches else
        "latest head log_id differs from bundle checkpoint",
    )
    if effective_policy.expected_log_id is not None:
        expected_latest = latest_head.log_id == effective_policy.expected_log_id
        _record(
            checks,
            "latest_expected_log_identity",
            expected_latest,
            "latest head log identity accepted" if expected_latest else
            "latest head log_id is not trusted",
        )

    latest_time_ok = latest_head.created_at_utc >= parsed_bundle.tree_head.created_at_utc
    _record(
        checks,
        "latest_checkpoint_time",
        latest_time_ok,
        "latest checkpoint time does not regress" if latest_time_ok else
        "latest checkpoint timestamp regressed",
    )
    future_limit = verified_at + timedelta(seconds=effective_policy.max_future_skew_seconds)
    latest_future_ok = latest_head.created_at_utc <= future_limit
    _record(
        checks,
        "latest_checkpoint_future_skew",
        latest_future_ok,
        "latest checkpoint time is plausible" if latest_future_ok else
        "latest checkpoint timestamp is too far in the future",
    )

    latest_signature_verified, latest_signature_reason = _verify_tree_head_trust(
        latest_head,
        effective_trust_store,
    )
    if effective_policy.require_tree_head_signature:
        _record(
            checks,
            "latest_tree_head_signature",
            latest_signature_verified,
            latest_signature_reason,
        )
    elif _has_any_signature_field(latest_head):
        _record(
            checks,
            "latest_tree_head_signature",
            latest_signature_verified,
            latest_signature_reason,
        )
    else:
        _record(
            checks,
            "latest_tree_head_signature",
            True,
            "unsigned latest checkpoint accepted only because policy explicitly allows it",
        )

    continuity_verified = False
    previous_head = parsed_bundle.tree_head
    if latest_head.tree_size < previous_head.tree_size:
        _record(checks, "append_only_continuity", False, "latest tree size regressed")
    elif latest_head.tree_size == previous_head.tree_size:
        same_root = latest_head.root_hash == previous_head.root_hash
        _record(
            checks,
            "append_only_continuity",
            same_root,
            "latest head matches bundle checkpoint" if same_root else
            "same tree size has a different root",
        )
        continuity_verified = same_root
    else:
        query = urlencode(
            {
                "from_size": previous_head.tree_size,
                "to_size": latest_head.tree_size,
            }
        )
        consistency_payload = effective_transport.get_json(
            f"{endpoint}/api/v1/proofs/consistency?{query}",
            headers=effective_headers,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )
        consistency = _parse_consistency_proof(consistency_payload)
        consistency_result = verify_consistency_proof(consistency)
        contract_matches = (
            consistency.previous_tree_size == previous_head.tree_size
            and consistency.latest_tree_size == latest_head.tree_size
            and consistency.previous_root_hash == previous_head.root_hash
            and consistency.latest_root_hash == latest_head.root_hash
        )
        continuity_verified = consistency_result.valid and contract_matches
        if not consistency_result.valid:
            continuity_reason = consistency_result.reason
        elif not contract_matches:
            continuity_reason = "consistency proof does not bind the requested checkpoints"
        else:
            continuity_reason = (
                "append-only consistency from bundle checkpoint to latest head verified"
            )
        _record(
            checks,
            "append_only_continuity",
            continuity_verified,
            continuity_reason,
        )

    signature_verified = offline.signature_verified and latest_signature_verified
    outcome = _outcome(
        mode="online",
        bundle=parsed_bundle,
        checks=checks,
        verified_at_utc=verified_at,
        signature_verified=signature_verified,
        continuity_verified=continuity_verified,
        standing_status="current_log",
        latest_head=latest_head,
    )
    if not continuity_verified and outcome.valid:
        raise AssertionError("online verifier cannot be valid without continuity verification")
    return outcome


def _verify_tree_head_trust(
    tree_head: SignedTreeHead,
    trust_store: TreeHeadTrustStore,
) -> tuple[bool, str]:
    fields = (tree_head.signature_alg, tree_head.signature, tree_head.public_key_id)
    if all(value is None for value in fields):
        return False, "tree head is unsigned"
    if any(value is None for value in fields):
        return False, "tree head signing envelope is incomplete"

    key_id = tree_head.public_key_id
    if key_id is None:
        return False, "tree head public_key_id is missing"
    trusted_key = trust_store.get(key_id)
    if trusted_key is None:
        return False, "tree head signing key is not in the verifier trust store"
    if tree_head.signature_alg != trusted_key.signature_alg:
        return False, "tree head signature algorithm does not match trusted key policy"

    signed_at = tree_head.created_at_utc
    if trusted_key.not_before_utc is not None and signed_at < trusted_key.not_before_utc:
        return False, "tree head predates trusted key validity"
    if trusted_key.not_after_utc is not None and signed_at > trusted_key.not_after_utc:
        return False, "tree head was signed after trusted key validity ended"
    if trusted_key.revoked_at_utc is not None and signed_at >= trusted_key.revoked_at_utc:
        return False, "tree head was signed at or after trusted key revocation"

    valid = verify_tree_head_signature(tree_head, trusted_key.public_key_hex)
    return valid, "tree head signature is trusted" if valid else "tree head signature is invalid"


def _has_any_signature_field(tree_head: SignedTreeHead) -> bool:
    return any(
        value is not None
        for value in (tree_head.signature_alg, tree_head.signature, tree_head.public_key_id)
    )


def _validated_base_url(
    base_url: str,
    *,
    allowed_hosts: tuple[str, ...],
    allow_insecure_http: bool,
) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"https", "http"} or parsed.hostname is None:
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base_url must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain a query string or fragment")
    if parsed.scheme != "https" and not allow_insecure_http:
        raise ValueError("online verification requires HTTPS unless allow_insecure_http is set")

    normalized_allowed_hosts = {host.lower() for host in allowed_hosts}
    if normalized_allowed_hosts and parsed.hostname.lower() not in normalized_allowed_hosts:
        raise ValueError("base_url host is not in the verifier allowlist")

    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _parse_bundle(bundle: EvidenceProofBundle | Mapping[str, Any]) -> EvidenceProofBundle:
    if isinstance(bundle, EvidenceProofBundle):
        return bundle
    try:
        return EvidenceProofBundle.model_validate(bundle)
    except ValidationError:
        return EvidenceProofBundle.model_validate_json(json.dumps(bundle))


def _parse_tree_head(tree_head: Mapping[str, Any]) -> SignedTreeHead:
    try:
        return SignedTreeHead.model_validate(tree_head)
    except ValidationError:
        return SignedTreeHead.model_validate_json(json.dumps(tree_head))


def _parse_consistency_proof(proof: Mapping[str, Any]) -> ConsistencyProof:
    try:
        return ConsistencyProof.model_validate(proof)
    except ValidationError:
        return ConsistencyProof.model_validate_json(json.dumps(proof))


def _normalize_verification_time(value: datetime | None) -> datetime:
    verified_at = value or datetime.now(UTC)
    if verified_at.tzinfo is None or verified_at.utcoffset() is None:
        raise ValueError("verified_at_utc must be timezone-aware")
    return verified_at.astimezone(UTC)


def _record(
    checks: list[VerificationCheck],
    code: str,
    passed: bool,
    reason: str,
) -> None:
    checks.append(VerificationCheck(code=code, passed=passed, reason=reason))


def _outcome(
    *,
    mode: VerifierMode,
    bundle: EvidenceProofBundle,
    checks: list[VerificationCheck],
    verified_at_utc: datetime,
    signature_verified: bool,
    continuity_verified: bool,
    standing_status: StandingStatus,
    latest_head: SignedTreeHead | None = None,
) -> VerifierOutcome:
    valid = all(check.passed for check in checks)
    reason = "ok"
    if not valid:
        reason = next(check.reason for check in checks if not check.passed)
    return VerifierOutcome(
        valid=valid,
        mode=mode,
        reason=reason,
        event_id=bundle.event.event_id,
        log_id=bundle.tree_head.log_id,
        event_hash=bundle.event_hash,
        leaf_hash=bundle.leaf_hash,
        checkpoint_root_hash=bundle.tree_head.root_hash,
        checkpoint_tree_size=bundle.tree_head.tree_size,
        latest_root_hash=latest_head.root_hash if latest_head is not None else None,
        latest_tree_size=latest_head.tree_size if latest_head is not None else None,
        signature_verified=signature_verified,
        continuity_verified=continuity_verified,
        standing_status=standing_status,
        checks=checks,
        verified_at_utc=verified_at_utc,
    )


__all__ = [
    "JSONTransport",
    "StdlibJSONTransport",
    "TreeHeadTrustStore",
    "TrustedTreeHeadKey",
    "VerificationCheck",
    "VerificationTransportError",
    "VerifierOutcome",
    "VerifierPolicy",
    "verify_offline_bundle",
    "verify_online_event",
]
