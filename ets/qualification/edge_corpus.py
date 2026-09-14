"""Executable contract for the ETS Edge Hardware Qualification Corpus v1.

HQP-3 translates historical Edge requirements into an executable, traceable corpus.
This module validates the corpus against the normative HQP profile and validates a
captured HQP-1 run against the Edge-specific execution requirements.

The producer-side helper can seal a complete run only as ``lab_tested``. It cannot
self-promote a DUT to ``qualified``; that remains an HQP-2 independent-verifier decision.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ets.qualification.hardware import (
    HardwareQualificationReport,
    HardwareQualificationRun,
    QualificationDisposition,
    TestStatus,
    build_qualification_report,
    seal_qualification_run,
)
from ets.qualification.profile import HardwareQualificationProfile


class EdgeExecutionMode(StrEnum):
    AUTOMATED_OR_OPERATOR_ASSISTED = "automated_or_operator_assisted"
    OPERATOR_ASSISTED = "operator_assisted"
    PHYSICAL_FAULT_INJECTION = "physical_fault_injection"
    OBSERVATION_ONLY = "observation_only"


class StrictEdgeCorpusModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class EdgeReferenceTargetClass(StrictEdgeCorpusModel):
    target_class_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4096)
    required_device_firmware_fields: tuple[str, ...] = Field(min_length=1)
    required_environment_dimensions: tuple[str, ...] = Field(min_length=1)
    minimum_lab_controls: tuple[str, ...] = Field(min_length=1)
    non_claims: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_target_fields(self) -> EdgeReferenceTargetClass:
        _require_unique(self.required_device_firmware_fields, "required device firmware fields")
        _require_unique(self.required_environment_dimensions, "required environment dimensions")
        _require_unique(self.minimum_lab_controls, "minimum lab controls")
        _require_unique(self.non_claims, "target non-claims")
        return self


class EdgeQualificationCase(StrictEdgeCorpusModel):
    test_id: str = Field(min_length=2, max_length=128)
    family: str = Field(min_length=1, max_length=128)
    requirement_refs: tuple[str, ...] = Field(min_length=1)
    execution_mode: EdgeExecutionMode
    driver_id: str = Field(min_length=1, max_length=256)
    preconditions: tuple[str, ...] = Field(min_length=1)
    required_artifact_roles: tuple[str, ...] = Field(min_length=1)
    assertion_ids: tuple[str, ...] = Field(min_length=1)
    recovery_boundary: str = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def require_unique_case_fields(self) -> EdgeQualificationCase:
        _require_unique(self.requirement_refs, f"{self.test_id} requirement refs")
        _require_unique(self.preconditions, f"{self.test_id} preconditions")
        _require_unique(self.required_artifact_roles, f"{self.test_id} artifact roles")
        _require_unique(self.assertion_ids, f"{self.test_id} assertion IDs")
        if not any(ref in {"#140", "#141", "#142", "#143", "#144", "#145"} for ref in self.requirement_refs):
            raise ValueError(f"{self.test_id} must trace to Edge requirements #140-#145")
        return self


class EdgeHardwareQualificationCorpus(StrictEdgeCorpusModel):
    schema_version: Literal["ets.edge-hardware-qualification-corpus.v1"]
    corpus_id: Literal["ets.edge.hardware-qualification.corpus.v1"]
    corpus_version: str = Field(min_length=1, max_length=128)
    profile_id: Literal["ets.edge.hardware-qualification.v1"]
    profile_version: str = Field(min_length=1, max_length=128)
    reference_target_class: EdgeReferenceTargetClass
    case_order: tuple[str, ...] = Field(min_length=1)
    cases: tuple[EdgeQualificationCase, ...] = Field(min_length=1)
    traceability_rule: str = Field(min_length=1, max_length=4096)
    claim_boundary: Literal[
        "bounded_edge_hardware_qualification_corpus_not_a_physical_qualification_result"
    ]

    @model_validator(mode="after")
    def require_complete_ordering(self) -> EdgeHardwareQualificationCorpus:
        _require_unique(self.case_order, "case order")
        case_ids = tuple(case.test_id for case in self.cases)
        _require_unique(case_ids, "corpus case IDs")
        if set(case_ids) != set(self.case_order):
            raise ValueError("case_order must contain every corpus case exactly once")
        return self


def load_edge_corpus(raw: bytes) -> EdgeHardwareQualificationCorpus:
    return EdgeHardwareQualificationCorpus.model_validate_json(raw)


def load_edge_profile(raw: bytes) -> HardwareQualificationProfile:
    return HardwareQualificationProfile.model_validate_json(raw)


def validate_edge_corpus_against_profile(
    profile: HardwareQualificationProfile,
    corpus: EdgeHardwareQualificationCorpus,
) -> None:
    """Require a one-to-one, versioned mapping between the HQP profile and Edge corpus."""

    if profile.profile_id != corpus.profile_id:
        raise ValueError("corpus profile_id does not match supplied HQP profile")
    if profile.profile_version != corpus.profile_version:
        raise ValueError("corpus profile_version does not match supplied HQP profile")

    profile_cases = {case.test_id: case for case in profile.test_cases}
    corpus_cases = {case.test_id: case for case in corpus.cases}
    if set(profile_cases) != set(corpus_cases):
        missing = sorted(set(profile_cases) - set(corpus_cases))
        extra = sorted(set(corpus_cases) - set(profile_cases))
        raise ValueError(f"profile/corpus test mismatch: missing={missing}, extra={extra}")

    for test_id in corpus.case_order:
        profile_case = profile_cases[test_id]
        corpus_case = corpus_cases[test_id]
        if not profile_case.required:
            raise ValueError(f"{test_id} must remain required in Edge profile v1")
        if profile_case.safety_boundary is None:
            raise ValueError(f"{test_id} requires an explicit HQP safety boundary")
        if not corpus_case.recovery_boundary:
            raise ValueError(f"{test_id} requires an explicit corpus recovery boundary")

    required_sources = {"#140", "#141", "#142", "#143", "#144", "#145"}
    observed_sources = {ref for case in corpus.cases for ref in case.requirement_refs}
    missing_sources = sorted(required_sources - observed_sources)
    if missing_sources:
        raise ValueError(f"corpus does not retain all Edge source issues: {missing_sources}")


def validate_edge_run_against_corpus(
    profile: HardwareQualificationProfile,
    corpus: EdgeHardwareQualificationCorpus,
    run: HardwareQualificationRun,
) -> None:
    """Validate a captured HQP-1 run against Edge-specific corpus semantics."""

    validate_edge_corpus_against_profile(profile, corpus)

    if run.profile.profile_id != profile.profile_id:
        raise ValueError("run profile_id does not match Edge profile")
    if run.profile.profile_version != profile.profile_version:
        raise ValueError("run profile_version does not match Edge profile")

    missing_firmware = sorted(
        set(corpus.reference_target_class.required_device_firmware_fields) - set(run.device.firmware)
    )
    if missing_firmware:
        raise ValueError(f"run device identity is missing claim-critical firmware fields: {missing_firmware}")

    missing_dimensions = sorted(
        set(corpus.reference_target_class.required_environment_dimensions)
        - set(run.environment.dimensions)
    )
    if missing_dimensions:
        raise ValueError(f"run environment is missing required dimensions: {missing_dimensions}")

    executions = {item.test_id: item for item in run.test_executions}
    unknown_executions = sorted(set(executions) - set(corpus.case_order))
    if unknown_executions:
        raise ValueError(f"run contains test executions outside Edge corpus v1: {unknown_executions}")

    missing_executions = sorted(set(corpus.case_order) - set(executions))
    if missing_executions:
        raise ValueError(f"run is missing Edge corpus executions: {missing_executions}")

    profile_cases = {case.test_id: case for case in profile.test_cases}
    corpus_cases = {case.test_id: case for case in corpus.cases}
    stimuli = {item.stimulus_id: item for item in run.stimuli}
    observations = {item.observation_id: item for item in run.observations}
    artifacts = {item.artifact_id: item for item in run.artifacts}

    for test_id in corpus.case_order:
        execution = executions[test_id]
        profile_case = profile_cases[test_id]
        corpus_case = corpus_cases[test_id]

        if execution.required != profile_case.required:
            raise ValueError(f"{test_id} required flag does not match Edge profile")

        stimulus_classes = {
            stimuli[stimulus_id].stimulus_class
            for stimulus_id in execution.stimulus_ids
            if stimulus_id in stimuli
        }
        if profile_case.stimulus_class not in stimulus_classes:
            raise ValueError(
                f"{test_id} is missing stimulus class {profile_case.stimulus_class!r}"
            )

        observation_classes = {
            observations[observation_id].observation_class
            for observation_id in execution.observation_ids
            if observation_id in observations
        }
        missing_observations = sorted(
            set(profile_case.required_observations) - observation_classes
        )
        if missing_observations:
            raise ValueError(
                f"{test_id} is missing required observation classes: {missing_observations}"
            )

        assertion_ids = {item.assertion_id for item in execution.assertions}
        missing_assertions = sorted(set(corpus_case.assertion_ids) - assertion_ids)
        if missing_assertions:
            raise ValueError(f"{test_id} is missing corpus assertions: {missing_assertions}")

        artifact_roles = {
            artifacts[artifact_id].artifact_role
            for artifact_id in execution.artifact_ids
            if artifact_id in artifacts
        }
        missing_roles = sorted(set(corpus_case.required_artifact_roles) - artifact_roles)
        if missing_roles:
            raise ValueError(f"{test_id} is missing required artifact roles: {missing_roles}")

        if execution.status is TestStatus.WAIVED and not profile_case.waivable:
            raise ValueError(f"{test_id} is non-waivable in Edge profile v1")


def seal_edge_lab_run(
    profile: HardwareQualificationProfile,
    corpus: EdgeHardwareQualificationCorpus,
    run: HardwareQualificationRun,
    *,
    completed_at: datetime,
) -> tuple[HardwareQualificationRun, HardwareQualificationReport]:
    """Seal a complete Edge capture as lab-tested, ready for HQP-2 verification."""

    if run.final_disposition is not QualificationDisposition.IN_PROGRESS:
        raise ValueError("Edge lab-run sealing requires an in-progress draft run")
    if run.run_digest_sha256 is not None:
        raise ValueError("Edge lab-run sealing requires an unsealed draft run")

    validate_edge_run_against_corpus(profile, corpus, run)

    executions = {item.test_id: item for item in run.test_executions}
    for profile_case in profile.test_cases:
        execution = executions[profile_case.test_id]
        if execution.status in {TestStatus.INVALID, TestStatus.NOT_RUN}:
            raise ValueError(
                f"{profile_case.test_id} is incomplete/invalid and cannot produce a lab-tested package"
            )
        if execution.status is TestStatus.FAILED:
            raise ValueError(
                f"{profile_case.test_id} failed; emit a failed run instead of lab-tested"
            )
        if execution.status is TestStatus.WAIVED and not profile_case.waivable:
            raise ValueError(f"{profile_case.test_id} cannot be waived")

    sealed = seal_qualification_run(
        run,
        final_disposition=QualificationDisposition.LAB_TESTED,
        completed_at=completed_at,
    )
    report = build_qualification_report(sealed)
    return sealed, report


def render_edge_execution_plan(corpus: EdgeHardwareQualificationCorpus) -> str:
    lines = [
        f"Edge HQP corpus: {corpus.corpus_id} @ {corpus.corpus_version}",
        f"Target class: {corpus.reference_target_class.target_class_id}",
        "Cases:",
    ]
    cases = {case.test_id: case for case in corpus.cases}
    for index, test_id in enumerate(corpus.case_order, start=1):
        case = cases[test_id]
        lines.append(
            f"{index:02d}. {test_id} [{case.execution_mode.value}] "
            f"{case.family} -> {case.driver_id}"
        )
        lines.append(f"    requirements: {', '.join(case.requirement_refs)}")
        lines.append(f"    recovery: {case.recovery_boundary}")
    lines.append(f"Claim boundary: {corpus.claim_boundary}")
    return "\n".join(lines) + "\n"


def _require_unique(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("completed-at must include a timezone offset")
    return parsed


def _write_json(path: Path, value: BaseModel) -> None:
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETS Edge HQP-3 corpus tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-corpus")
    validate_parser.add_argument("--profile", type=Path, required=True)
    validate_parser.add_argument("--corpus", type=Path, required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--corpus", type=Path, required=True)

    run_parser = subparsers.add_parser("validate-run")
    run_parser.add_argument("--profile", type=Path, required=True)
    run_parser.add_argument("--corpus", type=Path, required=True)
    run_parser.add_argument("--run", type=Path, required=True)

    seal_parser = subparsers.add_parser("seal-lab-run")
    seal_parser.add_argument("--profile", type=Path, required=True)
    seal_parser.add_argument("--corpus", type=Path, required=True)
    seal_parser.add_argument("--run", type=Path, required=True)
    seal_parser.add_argument("--completed-at", required=True)
    seal_parser.add_argument("--output-run", type=Path, required=True)
    seal_parser.add_argument("--output-report", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "plan":
        corpus = load_edge_corpus(args.corpus.read_bytes())
        print(render_edge_execution_plan(corpus), end="")
        return 0

    profile = load_edge_profile(args.profile.read_bytes())
    corpus = load_edge_corpus(args.corpus.read_bytes())

    if args.command == "validate-corpus":
        validate_edge_corpus_against_profile(profile, corpus)
        return 0

    run = HardwareQualificationRun.model_validate_json(args.run.read_bytes())
    if args.command == "validate-run":
        validate_edge_run_against_corpus(profile, corpus, run)
        return 0

    if args.command == "seal-lab-run":
        sealed, report = seal_edge_lab_run(
            profile,
            corpus,
            run,
            completed_at=_parse_datetime(args.completed_at),
        )
        _write_json(args.output_run, sealed)
        _write_json(args.output_report, report)
        return 0

    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EdgeExecutionMode",
    "EdgeHardwareQualificationCorpus",
    "EdgeQualificationCase",
    "EdgeReferenceTargetClass",
    "load_edge_corpus",
    "load_edge_profile",
    "main",
    "render_edge_execution_plan",
    "seal_edge_lab_run",
    "validate_edge_corpus_against_profile",
    "validate_edge_run_against_corpus",
]
