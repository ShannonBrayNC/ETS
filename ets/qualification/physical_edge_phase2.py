"""Wave 1 Edge Compact R0 sustained-capture and proof-verification evidence.

W1-3 covers R0.3 only. It records a bounded normal-operation capture session after
W1-2 has passed, binds every authoritative webhook acknowledgement to retained event,
proof, bundle, and tree-head artifacts, and records independent inclusion-proof
verification receipts produced away from the DUT.

The tooling records and evaluates evidence. It does not generate load, alter networking,
interrupt power, fill storage, change time, or make a hardware qualification claim.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ets.core.canonical_json import canonical_sha256
from ets.edge.webhook_adapter import WebhookCaptureReceipt
from ets.qualification.physical_edge import (
    EdgeCompactR0BenchManifest,
    load_manifest,
    readiness_issues,
)
from ets.qualification.physical_edge_phase1 import (
    EdgeR0Phase1Evaluation,
    load_phase1_evaluation,
    sha256_file,
)

_SHA256_RE = r"^[0-9a-f]{64}$"
_PHASE2_CLAIM_BOUNDARY: Literal[
    "r0_3_phase_evidence_not_a_physical_qualification_result"
] = "r0_3_phase_evidence_not_a_physical_qualification_result"
_PHASE2_DISPOSITION: Literal["phase_evidence_only"] = "phase_evidence_only"
_MIN_SUSTAINED_EVENTS = 100
_MIN_SUSTAINED_SECONDS = 60


class StrictPhase2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeR0SustainedCaptureSession(StrictPhase2Model):
    schema_version: Literal["ets.edge-compact-r0-sustained-capture-session.v1"] = (
        "ets.edge-compact-r0-sustained-capture-session.v1"
    )
    session_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase1_evaluation_id: str = Field(min_length=1, max_length=256)
    phase1_evaluation_sha256: str = Field(pattern=_SHA256_RE)
    source_id: str = Field(min_length=1, max_length=64)
    controller_id: str = Field(min_length=1, max_length=256)
    observer_id: str = Field(min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    attempted_event_count: int = Field(ge=1)
    workload_plan_sha256: str = Field(pattern=_SHA256_RE)
    resource_observation_sha256: str = Field(pattern=_SHA256_RE)
    controller_receipt_sha256: str = Field(pattern=_SHA256_RE)
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "r0_3_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE2_CLAIM_BOUNDARY

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("R0.3 session timestamps must include a timezone offset")
        return value

    @model_validator(mode="after")
    def require_sustained_window(self) -> EdgeR0SustainedCaptureSession:
        if self.completed_at < self.started_at:
            raise ValueError("R0.3 completed_at must not precede started_at")
        elapsed = (self.completed_at - self.started_at).total_seconds()
        if elapsed < _MIN_SUSTAINED_SECONDS:
            raise ValueError(
                f"R0.3 baseline requires at least {_MIN_SUSTAINED_SECONDS} seconds"
            )
        if self.attempted_event_count < _MIN_SUSTAINED_EVENTS:
            raise ValueError(
                f"R0.3 baseline requires at least {_MIN_SUSTAINED_EVENTS} attempted events"
            )
        return self


class EdgeR0CaptureRecord(StrictPhase2Model):
    schema_version: Literal["ets.edge-compact-r0-capture-record.v1"] = (
        "ets.edge-compact-r0-capture-record.v1"
    )
    record_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    sequence_number: int = Field(ge=1)
    captured_at: datetime
    request_payload_sha256: str = Field(pattern=_SHA256_RE)
    receipt_artifact_sha256: str = Field(pattern=_SHA256_RE)
    event_id: str = Field(min_length=1, max_length=256)
    evidence_id: str = Field(min_length=1, max_length=512)
    log_index: int = Field(ge=0)
    event_hash: str = Field(pattern=_SHA256_RE)
    content_hash: str = Field(pattern=_SHA256_RE)
    content_hash_alg: Literal["sha256"] = "sha256"
    byte_size: int = Field(gt=0)
    event_artifact_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    bundle_artifact_sha256: str = Field(pattern=_SHA256_RE)
    tree_head_artifact_sha256: str = Field(pattern=_SHA256_RE)
    authoritative_acknowledged: Literal[True] = True
    local_commit_observed: Literal[True] = True
    raw_payload_embedded: Literal[False] = False
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "r0_3_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE2_CLAIM_BOUNDARY

    @field_validator("captured_at")
    @classmethod
    def require_capture_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("R0.3 capture timestamp must include a timezone offset")
        return value

    @model_validator(mode="after")
    def bind_payload_to_edge_content_hash(self) -> EdgeR0CaptureRecord:
        if self.request_payload_sha256 != self.content_hash:
            raise ValueError("request payload SHA-256 must match Edge content_hash")
        return self


class EdgeR0IndependentProofReceipt(StrictPhase2Model):
    schema_version: Literal["ets.edge-compact-r0-proof-verification-receipt.v1"] = (
        "ets.edge-compact-r0-proof-verification-receipt.v1"
    )
    verification_id: str = Field(min_length=1, max_length=256)
    record_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    event_id: str = Field(min_length=1, max_length=256)
    verified_at: datetime
    verifier_id: str = Field(min_length=1, max_length=256)
    verifier_host_id: str = Field(min_length=1, max_length=256)
    verifier_build_sha256: str = Field(pattern=_SHA256_RE)
    proof_artifact_sha256: str = Field(pattern=_SHA256_RE)
    verification_result_sha256: str = Field(pattern=_SHA256_RE)
    inclusion_valid: bool
    independent_execution_context: bool
    credentials_embedded: Literal[False] = False
    private_keys_embedded: Literal[False] = False
    claim_boundary: Literal[
        "r0_3_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE2_CLAIM_BOUNDARY

    @field_validator("verified_at")
    @classmethod
    def require_verification_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("proof verification timestamp must include a timezone offset")
        return value


class EdgeR0Phase2Evaluation(StrictPhase2Model):
    schema_version: Literal["ets.edge-compact-r0-phase2-evaluation.v1"] = (
        "ets.edge-compact-r0-phase2-evaluation.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=256)
    manifest_id: str = Field(min_length=1, max_length=256)
    asset_id: str = Field(min_length=1, max_length=256)
    phase1_evaluation_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    evaluated_at: datetime
    attempted_event_count: int = Field(ge=0)
    authoritative_ack_count: int = Field(ge=0)
    committed_record_count: int = Field(ge=0)
    independently_verified_count: int = Field(ge=0)
    r0_3_passed: bool
    issues: tuple[str, ...]
    disposition: Literal["phase_evidence_only"] = _PHASE2_DISPOSITION
    claim_boundary: Literal[
        "r0_3_phase_evidence_not_a_physical_qualification_result"
    ] = _PHASE2_CLAIM_BOUNDARY

    @field_validator("evaluated_at")
    @classmethod
    def require_evaluation_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("R0.3 evaluation timestamp must include a timezone offset")
        return value

    @model_validator(mode="after")
    def enforce_evaluation_result(self) -> EdgeR0Phase2Evaluation:
        if self.r0_3_passed and self.issues:
            raise ValueError("passing R0.3 evaluation cannot retain blocking issues")
        return self


def load_capture_session(raw: bytes) -> EdgeR0SustainedCaptureSession:
    return EdgeR0SustainedCaptureSession.model_validate_json(raw)


def load_capture_record(raw: bytes) -> EdgeR0CaptureRecord:
    return EdgeR0CaptureRecord.model_validate_json(raw)


def load_proof_receipt(raw: bytes) -> EdgeR0IndependentProofReceipt:
    return EdgeR0IndependentProofReceipt.model_validate_json(raw)


def build_capture_session(
    manifest: EdgeCompactR0BenchManifest,
    phase1: EdgeR0Phase1Evaluation,
    *,
    session_id: str,
    source_id: str,
    controller_id: str,
    started_at: datetime,
    completed_at: datetime,
    attempted_event_count: int,
    workload_plan_sha256: str,
    resource_observation_sha256: str,
    controller_receipt_sha256: str,
) -> EdgeR0SustainedCaptureSession:
    blockers = readiness_issues(manifest)
    if blockers:
        raise ValueError("bench manifest is not ready for R0.3 execution")
    if not phase1.phase1_passed:
        raise ValueError("W1-2 R0.1/R0.2 phase evidence must pass before R0.3")

    asset_id = _require_present(manifest.dut.asset_id, "DUT asset_id")
    observer_id = _require_present(manifest.observer.observer_id, "observer_id")
    if phase1.manifest_id != manifest.manifest_id or phase1.asset_id != asset_id:
        raise ValueError("W1-2 evaluation does not bind to the R0.3 DUT manifest")

    return EdgeR0SustainedCaptureSession(
        session_id=session_id,
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase1_evaluation_id=phase1.evaluation_id,
        phase1_evaluation_sha256=canonical_sha256(phase1.model_dump(mode="json")),
        source_id=source_id,
        controller_id=controller_id,
        observer_id=observer_id,
        started_at=started_at,
        completed_at=completed_at,
        attempted_event_count=attempted_event_count,
        workload_plan_sha256=_validate_sha256(workload_plan_sha256),
        resource_observation_sha256=_validate_sha256(resource_observation_sha256),
        controller_receipt_sha256=_validate_sha256(controller_receipt_sha256),
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def build_capture_record(
    session: EdgeR0SustainedCaptureSession,
    receipt: WebhookCaptureReceipt,
    *,
    sequence_number: int,
    captured_at: datetime,
    request_payload_sha256: str,
    receipt_artifact_sha256: str,
    event_artifact_sha256: str,
    proof_artifact_sha256: str,
    bundle_artifact_sha256: str,
    tree_head_artifact_sha256: str,
) -> EdgeR0CaptureRecord:
    request_digest = _validate_sha256(request_payload_sha256)
    content_digest = _validate_sha256(receipt.content_hash)
    event_hash = _validate_sha256(receipt.event_hash)
    seed = {
        "session_id": session.session_id,
        "sequence_number": sequence_number,
        "event_id": receipt.event_id,
        "event_hash": event_hash,
        "content_hash": content_digest,
    }

    return EdgeR0CaptureRecord(
        record_id=f"edge-r0-capture-{canonical_sha256(seed)[:24]}",
        session_id=session.session_id,
        sequence_number=sequence_number,
        captured_at=captured_at,
        request_payload_sha256=request_digest,
        receipt_artifact_sha256=_validate_sha256(receipt_artifact_sha256),
        event_id=receipt.event_id,
        evidence_id=receipt.evidence_id,
        log_index=receipt.log_index,
        event_hash=event_hash,
        content_hash=content_digest,
        content_hash_alg="sha256",
        byte_size=receipt.byte_size,
        event_artifact_sha256=_validate_sha256(event_artifact_sha256),
        proof_artifact_sha256=_validate_sha256(proof_artifact_sha256),
        bundle_artifact_sha256=_validate_sha256(bundle_artifact_sha256),
        tree_head_artifact_sha256=_validate_sha256(tree_head_artifact_sha256),
        authoritative_acknowledged=True,
        local_commit_observed=True,
        raw_payload_embedded=False,
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def build_proof_receipt(
    record: EdgeR0CaptureRecord,
    verification_result: dict[str, object],
    *,
    verifier_id: str,
    verifier_host_id: str,
    verifier_build_sha256: str,
    proof_artifact_sha256: str,
    verification_result_sha256: str,
    verified_at: datetime,
    independent_execution_context: bool,
) -> EdgeR0IndependentProofReceipt:
    result_valid = verification_result.get("valid") is True
    proof_digest = _validate_sha256(proof_artifact_sha256)
    seed = {
        "record_id": record.record_id,
        "event_id": record.event_id,
        "proof_artifact_sha256": proof_digest,
        "verification_result_sha256": verification_result_sha256,
        "verifier_host_id": verifier_host_id,
        "verified_at": verified_at.isoformat(),
    }
    return EdgeR0IndependentProofReceipt(
        verification_id=f"edge-r0-verify-{canonical_sha256(seed)[:24]}",
        record_id=record.record_id,
        session_id=record.session_id,
        event_id=record.event_id,
        verified_at=verified_at,
        verifier_id=verifier_id,
        verifier_host_id=verifier_host_id,
        verifier_build_sha256=_validate_sha256(verifier_build_sha256),
        proof_artifact_sha256=proof_digest,
        verification_result_sha256=_validate_sha256(verification_result_sha256),
        inclusion_valid=result_valid,
        independent_execution_context=independent_execution_context,
        credentials_embedded=False,
        private_keys_embedded=False,
    )


def evaluate_r0_3(
    manifest: EdgeCompactR0BenchManifest,
    phase1: EdgeR0Phase1Evaluation,
    session: EdgeR0SustainedCaptureSession,
    records: tuple[EdgeR0CaptureRecord, ...],
    proof_receipts: tuple[EdgeR0IndependentProofReceipt, ...],
    *,
    evaluated_at: datetime,
) -> EdgeR0Phase2Evaluation:
    issues: list[str] = []
    asset_id = manifest.dut.asset_id or "unknown-asset"

    for blocker in readiness_issues(manifest):
        issues.append(f"R0.3: bench manifest not ready: {blocker}")
    if not phase1.phase1_passed:
        issues.append("R0.3: W1-2 R0.1/R0.2 phase evidence did not pass")
    if phase1.manifest_id != manifest.manifest_id or phase1.asset_id != asset_id:
        issues.append("R0.3: W1-2 evaluation is bound to a different DUT manifest")

    expected_phase1_digest = canonical_sha256(phase1.model_dump(mode="json"))
    if session.manifest_id != manifest.manifest_id or session.asset_id != asset_id:
        issues.append("R0.3: capture session is bound to a different DUT manifest")
    if session.phase1_evaluation_id != phase1.evaluation_id:
        issues.append("R0.3: capture session references a different W1-2 evaluation")
    if session.phase1_evaluation_sha256 != expected_phase1_digest:
        issues.append("R0.3: W1-2 evaluation digest binding does not match")

    record_ids = [item.record_id for item in records]
    event_ids = [item.event_id for item in records]
    log_indices = [item.log_index for item in records]
    sequence_numbers = [item.sequence_number for item in records]
    if len(record_ids) != len(set(record_ids)):
        issues.append("R0.3: capture record IDs must be unique")
    if len(event_ids) != len(set(event_ids)):
        issues.append("R0.3: Edge event IDs must be unique")
    if len(log_indices) != len(set(log_indices)):
        issues.append("R0.3: Edge log indices must be unique")
    expected_sequences = list(range(1, session.attempted_event_count + 1))
    if sorted(sequence_numbers) != expected_sequences:
        issues.append("R0.3: capture records do not cover every attempted sequence exactly once")

    for record in records:
        if record.session_id != session.session_id:
            issues.append(f"R0.3: capture record {record.record_id} belongs to another session")
        if not record.authoritative_acknowledged or not record.local_commit_observed:
            issues.append(f"R0.3: capture record {record.record_id} lacks authoritative commit evidence")

    if len(records) != session.attempted_event_count:
        issues.append(
            "R0.3: authoritative acknowledgement/commit count does not equal attempted count"
        )

    receipts_by_record: dict[str, EdgeR0IndependentProofReceipt] = {}
    for receipt in proof_receipts:
        if receipt.record_id in receipts_by_record:
            issues.append(f"R0.3: duplicate proof verification for {receipt.record_id}")
            continue
        receipts_by_record[receipt.record_id] = receipt

    verifier_host = manifest.verifier.verifier_host_id
    for record in records:
        receipt = receipts_by_record.get(record.record_id)
        if receipt is None:
            issues.append(f"R0.3: missing independent proof verification for {record.record_id}")
            continue
        if receipt.session_id != session.session_id or receipt.event_id != record.event_id:
            issues.append(f"R0.3: proof verification binding mismatch for {record.record_id}")
        if receipt.proof_artifact_sha256 != record.proof_artifact_sha256:
            issues.append(f"R0.3: proof artifact digest mismatch for {record.record_id}")
        if not receipt.inclusion_valid:
            issues.append(f"R0.3: inclusion proof failed verification for {record.record_id}")
        if not receipt.independent_execution_context:
            issues.append(f"R0.3: verifier was not independent for {record.record_id}")
        if verifier_host is None or receipt.verifier_host_id != verifier_host:
            issues.append(f"R0.3: verifier host does not match bench binding for {record.record_id}")

    unknown_receipts = sorted(set(receipts_by_record) - set(record_ids))
    if unknown_receipts:
        issues.append(f"R0.3: proof receipts reference unknown capture records: {unknown_receipts}")

    verified_count = sum(
        1
        for record in records
        if (receipt := receipts_by_record.get(record.record_id)) is not None
        and receipt.inclusion_valid
        and receipt.independent_execution_context
        and receipt.proof_artifact_sha256 == record.proof_artifact_sha256
    )
    passed = not issues
    seed = {
        "manifest_id": manifest.manifest_id,
        "phase1_evaluation_id": phase1.evaluation_id,
        "session_id": session.session_id,
        "evaluated_at": evaluated_at.isoformat(),
        "record_ids": sorted(record_ids),
        "verification_ids": sorted(item.verification_id for item in proof_receipts),
        "issues": issues,
    }
    return EdgeR0Phase2Evaluation(
        evaluation_id=f"edge-r0-phase2-{canonical_sha256(seed)[:24]}",
        manifest_id=manifest.manifest_id,
        asset_id=asset_id,
        phase1_evaluation_id=phase1.evaluation_id,
        session_id=session.session_id,
        evaluated_at=evaluated_at,
        attempted_event_count=session.attempted_event_count,
        authoritative_ack_count=len(records),
        committed_record_count=len(records),
        independently_verified_count=verified_count,
        r0_3_passed=passed,
        issues=tuple(issues),
        disposition=_PHASE2_DISPOSITION,
        claim_boundary=_PHASE2_CLAIM_BOUNDARY,
    )


def _validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
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


def _load_json_object(path: Path) -> dict[str, object]:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETS Wave 1 Edge Compact R0 R0.3 evidence tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    session_parser = subparsers.add_parser("record-session")
    session_parser.add_argument("--manifest", type=Path, required=True)
    session_parser.add_argument("--phase1-evaluation", type=Path, required=True)
    session_parser.add_argument("--session-id", required=True)
    session_parser.add_argument("--source-id", required=True)
    session_parser.add_argument("--controller-id", required=True)
    session_parser.add_argument("--started-at", required=True)
    session_parser.add_argument("--completed-at", required=True)
    session_parser.add_argument("--attempted-events", type=int, required=True)
    session_parser.add_argument("--workload-plan", type=Path, required=True)
    session_parser.add_argument("--resource-observation", type=Path, required=True)
    session_parser.add_argument("--controller-receipt", type=Path, required=True)
    session_parser.add_argument("--output", type=Path, required=True)

    capture_parser = subparsers.add_parser("record-capture")
    capture_parser.add_argument("--session", type=Path, required=True)
    capture_parser.add_argument("--sequence", type=int, required=True)
    capture_parser.add_argument("--captured-at", required=True)
    capture_parser.add_argument("--request-payload", type=Path, required=True)
    capture_parser.add_argument("--receipt", type=Path, required=True)
    capture_parser.add_argument("--event", type=Path, required=True)
    capture_parser.add_argument("--proof", type=Path, required=True)
    capture_parser.add_argument("--bundle", type=Path, required=True)
    capture_parser.add_argument("--tree-head", type=Path, required=True)
    capture_parser.add_argument("--output", type=Path, required=True)

    verify_parser = subparsers.add_parser("record-verification")
    verify_parser.add_argument("--capture-record", type=Path, required=True)
    verify_parser.add_argument("--proof", type=Path, required=True)
    verify_parser.add_argument("--verification-result", type=Path, required=True)
    verify_parser.add_argument("--verifier-id", required=True)
    verify_parser.add_argument("--verifier-host-id", required=True)
    verify_parser.add_argument("--verifier-build-digest", required=True)
    verify_parser.add_argument("--verified-at", required=True)
    verify_parser.add_argument("--independent", action="store_true")
    verify_parser.add_argument("--output", type=Path, required=True)

    evaluate_parser = subparsers.add_parser("evaluate-r0-3")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--phase1-evaluation", type=Path, required=True)
    evaluate_parser.add_argument("--session", type=Path, required=True)
    evaluate_parser.add_argument("--capture-record", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--proof-receipt", type=Path, action="append", required=True)
    evaluate_parser.add_argument("--evaluated-at")
    evaluate_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "record-session":
        manifest = load_manifest(args.manifest.read_bytes())
        phase1 = load_phase1_evaluation(args.phase1_evaluation.read_bytes())
        session = build_capture_session(
            manifest,
            phase1,
            session_id=args.session_id,
            source_id=args.source_id,
            controller_id=args.controller_id,
            started_at=_parse_datetime(args.started_at),
            completed_at=_parse_datetime(args.completed_at),
            attempted_event_count=args.attempted_events,
            workload_plan_sha256=sha256_file(args.workload_plan),
            resource_observation_sha256=sha256_file(args.resource_observation),
            controller_receipt_sha256=sha256_file(args.controller_receipt),
        )
        _write_json(args.output, session)
        return 0

    if args.command == "record-capture":
        session = load_capture_session(args.session.read_bytes())
        receipt = WebhookCaptureReceipt.model_validate_json(args.receipt.read_bytes())
        record = build_capture_record(
            session,
            receipt,
            sequence_number=args.sequence,
            captured_at=_parse_datetime(args.captured_at),
            request_payload_sha256=sha256_file(args.request_payload),
            receipt_artifact_sha256=sha256_file(args.receipt),
            event_artifact_sha256=sha256_file(args.event),
            proof_artifact_sha256=sha256_file(args.proof),
            bundle_artifact_sha256=sha256_file(args.bundle),
            tree_head_artifact_sha256=sha256_file(args.tree_head),
        )
        _write_json(args.output, record)
        return 0

    if args.command == "record-verification":
        record = load_capture_record(args.capture_record.read_bytes())
        result = _load_json_object(args.verification_result)
        proof_receipt = build_proof_receipt(
            record,
            result,
            verifier_id=args.verifier_id,
            verifier_host_id=args.verifier_host_id,
            verifier_build_sha256=args.verifier_build_digest,
            proof_artifact_sha256=sha256_file(args.proof),
            verification_result_sha256=sha256_file(args.verification_result),
            verified_at=_parse_datetime(args.verified_at),
            independent_execution_context=args.independent,
        )
        _write_json(args.output, proof_receipt)
        return 0

    if args.command == "evaluate-r0-3":
        manifest = load_manifest(args.manifest.read_bytes())
        phase1 = load_phase1_evaluation(args.phase1_evaluation.read_bytes())
        session = load_capture_session(args.session.read_bytes())
        records = tuple(load_capture_record(path.read_bytes()) for path in args.capture_record)
        receipts = tuple(load_proof_receipt(path.read_bytes()) for path in args.proof_receipt)
        evaluated_at = (
            _parse_datetime(args.evaluated_at)
            if args.evaluated_at is not None
            else datetime.now(UTC)
        )
        evaluation = evaluate_r0_3(
            manifest,
            phase1,
            session,
            records,
            receipts,
            evaluated_at=evaluated_at,
        )
        _write_json(args.output, evaluation)
        return 0 if evaluation.r0_3_passed else 2

    raise AssertionError(f"unhandled command: {args.command}")
