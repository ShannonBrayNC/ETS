"""Portable verification package for the VectorRail/VRX consequence-custody demo.

The package is deliberately self-contained: it embeds the sealed actuation trial, the
VRX acceptance record, their Evidence Object projections, dependency edges, a bounded
verification receipt, observability limits, and a replay manifest. The package can be
verified offline without trusting a hosted ETS service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ets.core.canonical_json import canonicalize
from ets.evidence_object.canonical import object_hash
from ets.evidence_object.models import EvidenceObject
from ets.ranger.electromagnetic_actuation import trial_digest
from ets.ranger.electromagnetic_actuation_evidence_adapter import (
    electromagnetic_actuation_trial_to_evidence_object,
)
from ets.ranger.vectorrail_acceptance_evidence import (
    vectorrail_acceptance_digest,
    vectorrail_acceptance_to_evidence_object,
)
from ets.ranger.vectorrail_consequence_custody import (
    VectorRailConsequenceCustodyVerification,
    verify_vectorrail_consequence_custody,
)

_PACKAGE_SCHEMA = "ranger.vectorrail-vrx-consequence-custody-package.v0.1"
_REPLAY_MANIFEST_SCHEMA = "ets.vectorrail.consequence-custody-replay-manifest.v0.1"
_REPLAY_PROFILE = "ets.vectorrail.consequence-custody-replay.v0.1"
_VERIFIER_ENTRYPOINT = (
    "ets.ranger.vectorrail_consequence_custody.verify_vectorrail_consequence_custody"
)


class VectorRailConsequenceCustodyPackageError(ValueError):
    """Raised when a portable consequence-custody package is structurally invalid."""


class VectorRailConsequenceCustodyPackageVerification(BaseModel):
    """Result of independently replaying a portable VRX package."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    conclusion: str
    chain_conclusion: str
    package_id: str
    package_digest: str
    package_digest_valid: bool
    trial_record_digest_valid: bool
    acceptance_record_digest_valid: bool
    trial_object_hash_valid: bool
    acceptance_object_hash_valid: bool
    dependency_graph_valid: bool
    replay_receipt_matches: bool
    observability_boundary_conserved: bool
    network_required: bool
    truth_claim_supported: bool = False
    truth_claim_boundary: str = (
        "portable_replay_verifies_recorded_integrity_and_reconstruction_not_objective_"
        "physical_truth"
    )


def package_preimage(package: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical package preimage with the package digest removed."""

    payload = deepcopy(dict(package))
    if payload.get("schema_version") != _PACKAGE_SCHEMA:
        raise VectorRailConsequenceCustodyPackageError(
            f"schema_version must be {_PACKAGE_SCHEMA}"
        )
    payload.pop("package_digest", None)
    return payload


def package_digest(package: Mapping[str, Any]) -> str:
    """Return the deterministic SHA-256 digest for a portable package."""

    return f"sha256:{hashlib.sha256(canonicalize(package_preimage(package))).hexdigest()}"


def build_vectorrail_consequence_custody_package(
    trial: Mapping[str, Any],
    acceptance_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one deterministic, self-contained VRX verification package."""

    verification = verify_vectorrail_consequence_custody(trial, acceptance_record)
    trial_evidence = electromagnetic_actuation_trial_to_evidence_object(trial)
    acceptance_evidence = vectorrail_acceptance_to_evidence_object(acceptance_record)

    trial_id = verification.trial_id
    acceptance_id = verification.acceptance_id
    trial_record_digest = trial_digest(trial)
    acceptance_record_digest = vectorrail_acceptance_digest(acceptance_record)
    trial_object_digest = object_hash(trial_evidence)
    acceptance_object_digest = object_hash(acceptance_evidence)

    package: dict[str, Any] = {
        "schema_version": _PACKAGE_SCHEMA,
        "package_id": f"vrx-cc:{trial_id}:{acceptance_id}",
        "trial": {
            "record_digest": trial_record_digest,
            "object_hash": trial_object_digest,
            "record": deepcopy(dict(trial)),
            "evidence_object": trial_evidence.model_dump(mode="json", exclude_none=True),
        },
        "acceptance": {
            "record_digest": acceptance_record_digest,
            "object_hash": acceptance_object_digest,
            "record": deepcopy(dict(acceptance_record)),
            "evidence_object": acceptance_evidence.model_dump(mode="json", exclude_none=True),
        },
        "dependency_edges": _dependency_edges(trial_evidence, acceptance_evidence),
        "verification_receipt": verification.model_dump(mode="json"),
        "observability": _observability_record(verification),
        "replay_manifest": {
            "profile": _REPLAY_PROFILE,
            "verifier_entrypoint": _VERIFIER_ENTRYPOINT,
            "trial_input": "trial.record",
            "acceptance_input": "acceptance.record",
            "expected_chain_conclusion": verification.conclusion,
            "expected_trial_object_hash": trial_object_digest,
            "expected_acceptance_object_hash": acceptance_object_digest,
            "network_required": False,
        },
        "package_digest": None,
    }
    package["package_digest"] = package_digest(package)
    return package


def verify_vectorrail_consequence_custody_package(
    package: Mapping[str, Any],
) -> VectorRailConsequenceCustodyPackageVerification:
    """Replay and verify a portable package without relying on hosted services."""

    if package.get("schema_version") != _PACKAGE_SCHEMA:
        raise VectorRailConsequenceCustodyPackageError(
            f"schema_version must be {_PACKAGE_SCHEMA}"
        )
    package_id = _required_string(package, "package_id")
    stored_package_digest = _required_string(package, "package_digest")
    computed_package_digest = package_digest(package)
    package_digest_valid = stored_package_digest == computed_package_digest

    trial_section = _required_mapping(package, "trial")
    acceptance_section = _required_mapping(package, "acceptance")
    trial = _required_mapping(trial_section, "record")
    acceptance_record = _required_mapping(acceptance_section, "record")

    replay = verify_vectorrail_consequence_custody(trial, acceptance_record)

    trial_record_digest_valid = (
        _optional_string(trial_section.get("record_digest")) == trial_digest(trial)
    )
    acceptance_record_digest_valid = (
        _optional_string(acceptance_section.get("record_digest"))
        == vectorrail_acceptance_digest(acceptance_record)
    )

    fresh_trial_evidence = electromagnetic_actuation_trial_to_evidence_object(trial)
    fresh_acceptance_evidence = vectorrail_acceptance_to_evidence_object(acceptance_record)
    trial_object_hash_valid = _object_binding_valid(
        trial_section,
        fresh_trial_evidence,
    )
    acceptance_object_hash_valid = _object_binding_valid(
        acceptance_section,
        fresh_acceptance_evidence,
    )

    dependency_graph_valid = _normalized_edges(package.get("dependency_edges")) == _normalized_edges(
        _dependency_edges(fresh_trial_evidence, fresh_acceptance_evidence)
    )

    receipt = package.get("verification_receipt")
    replay_receipt_matches = isinstance(receipt, Mapping) and dict(receipt) == replay.model_dump(
        mode="json"
    )

    observability = package.get("observability")
    observability_boundary_conserved = (
        isinstance(observability, Mapping)
        and dict(observability) == _observability_record(replay)
    )

    replay_manifest = _required_mapping(package, "replay_manifest")
    network_required_value = replay_manifest.get("network_required")
    if not isinstance(network_required_value, bool):
        raise VectorRailConsequenceCustodyPackageError(
            "replay_manifest.network_required must be boolean"
        )
    manifest_valid = all(
        (
            replay_manifest.get("profile") == _REPLAY_PROFILE,
            replay_manifest.get("verifier_entrypoint") == _VERIFIER_ENTRYPOINT,
            replay_manifest.get("trial_input") == "trial.record",
            replay_manifest.get("acceptance_input") == "acceptance.record",
            replay_manifest.get("expected_chain_conclusion") == replay.conclusion,
            replay_manifest.get("expected_trial_object_hash")
            == object_hash(fresh_trial_evidence),
            replay_manifest.get("expected_acceptance_object_hash")
            == object_hash(fresh_acceptance_evidence),
            network_required_value is False,
        )
    )
    replay_receipt_matches = replay_receipt_matches and manifest_valid

    conclusion = _package_conclusion(
        package_digest_valid=package_digest_valid,
        trial_record_digest_valid=trial_record_digest_valid,
        acceptance_record_digest_valid=acceptance_record_digest_valid,
        trial_object_hash_valid=trial_object_hash_valid,
        acceptance_object_hash_valid=acceptance_object_hash_valid,
        dependency_graph_valid=dependency_graph_valid,
        replay_receipt_matches=replay_receipt_matches,
        observability_boundary_conserved=observability_boundary_conserved,
    )

    return VectorRailConsequenceCustodyPackageVerification(
        conclusion=conclusion,
        chain_conclusion=replay.conclusion,
        package_id=package_id,
        package_digest=computed_package_digest,
        package_digest_valid=package_digest_valid,
        trial_record_digest_valid=trial_record_digest_valid,
        acceptance_record_digest_valid=acceptance_record_digest_valid,
        trial_object_hash_valid=trial_object_hash_valid,
        acceptance_object_hash_valid=acceptance_object_hash_valid,
        dependency_graph_valid=dependency_graph_valid,
        replay_receipt_matches=replay_receipt_matches,
        observability_boundary_conserved=observability_boundary_conserved,
        network_required=network_required_value,
    )


def execute_vectorrail_replay_manifest(
    manifest_path: Path,
    *,
    output_path: Path | None = None,
) -> VectorRailConsequenceCustodyPackageVerification:
    """Execute a repo-oriented replay manifest and emit the portable JSON artifact."""

    manifest = _load_json(manifest_path)
    if manifest.get("manifest_version") != _REPLAY_MANIFEST_SCHEMA:
        raise VectorRailConsequenceCustodyPackageError(
            f"manifest_version must be {_REPLAY_MANIFEST_SCHEMA}"
        )

    root = manifest_path.parent
    trial_path = root / _required_string(manifest, "trial_path")
    acceptance_path = root / _required_string(manifest, "acceptance_path")
    trial = _load_json(trial_path)
    acceptance_record = _load_json(acceptance_path)

    seal_trial = manifest.get("seal_trial_if_missing", False)
    if not isinstance(seal_trial, bool):
        raise VectorRailConsequenceCustodyPackageError(
            "seal_trial_if_missing must be boolean"
        )
    if seal_trial and trial.get("trial_digest") is None:
        trial["trial_digest"] = trial_digest(trial)

    package = build_vectorrail_consequence_custody_package(trial, acceptance_record)
    result = verify_vectorrail_consequence_custody_package(package)

    expected_chain = _required_string(manifest, "expected_chain_conclusion")
    expected_package = _required_string(manifest, "expected_package_conclusion")
    if result.chain_conclusion != expected_chain:
        raise VectorRailConsequenceCustodyPackageError(
            "replayed chain conclusion did not match manifest expectation"
        )
    if result.conclusion != expected_package:
        raise VectorRailConsequenceCustodyPackageError(
            "portable package conclusion did not match manifest expectation"
        )

    destination_value = manifest.get("output_path")
    destination = output_path
    if destination is None and isinstance(destination_value, str) and destination_value:
        destination = root / destination_value
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(package, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result


def _object_binding_valid(
    section: Mapping[str, Any],
    fresh_evidence: EvidenceObject,
) -> bool:
    embedded = section.get("evidence_object")
    declared_hash = _optional_string(section.get("object_hash"))
    if not isinstance(embedded, Mapping) or declared_hash is None:
        return False
    try:
        embedded_evidence = EvidenceObject.model_validate(dict(embedded))
    except ValueError:
        return False
    expected_hash = object_hash(fresh_evidence)
    return object_hash(embedded_evidence) == expected_hash == declared_hash


def _dependency_edges(
    trial_evidence: EvidenceObject,
    acceptance_evidence: EvidenceObject,
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for source in (trial_evidence, acceptance_evidence):
        for relationship in source.relationships:
            edges.append(
                {
                    "source_evidence_id": source.identity.evidence_id,
                    "relationship_type": relationship.relationship_type.value,
                    "target_evidence_ref": relationship.target_evidence_ref,
                }
            )
    return sorted(
        edges,
        key=lambda item: (
            item["source_evidence_id"],
            item["relationship_type"],
            item["target_evidence_ref"],
        ),
    )


def _normalized_edges(value: object) -> tuple[tuple[str, str, str], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    edges: list[tuple[str, str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return ()
        source = _optional_string(item.get("source_evidence_id"))
        relationship = _optional_string(item.get("relationship_type"))
        target = _optional_string(item.get("target_evidence_ref"))
        if source is None or relationship is None or target is None:
            return ()
        edges.append((source, relationship, target))
    return tuple(sorted(edges))


def _observability_record(
    verification: VectorRailConsequenceCustodyVerification,
) -> dict[str, Any]:
    return {
        "independent_observation_groups": list(
            verification.independent_observation_groups
        ),
        "truth_claim_supported": verification.truth_claim_supported,
        "truth_claim_boundary": verification.truth_claim_boundary,
    }


def _package_conclusion(
    *,
    package_digest_valid: bool,
    trial_record_digest_valid: bool,
    acceptance_record_digest_valid: bool,
    trial_object_hash_valid: bool,
    acceptance_object_hash_valid: bool,
    dependency_graph_valid: bool,
    replay_receipt_matches: bool,
    observability_boundary_conserved: bool,
) -> str:
    if not package_digest_valid:
        return "PACKAGE_INTEGRITY_FAILURE"
    if not trial_record_digest_valid or not acceptance_record_digest_valid:
        return "RECORD_BINDING_FAILURE"
    if not trial_object_hash_valid or not acceptance_object_hash_valid:
        return "OBJECT_BINDING_FAILURE"
    if not dependency_graph_valid:
        return "DEPENDENCY_GRAPH_FAILURE"
    if not replay_receipt_matches:
        return "REPLAY_MISMATCH"
    if not observability_boundary_conserved:
        return "OBSERVABILITY_BOUNDARY_FAILURE"
    return "VERIFIED_REPLAYABLE"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VectorRailConsequenceCustodyPackageError(
            f"{path} must contain a JSON object"
        )
    return value


def _required_mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    result = value.get(field)
    if not isinstance(result, Mapping):
        raise VectorRailConsequenceCustodyPackageError(f"{field} must be an object")
    return result


def _required_string(value: Mapping[str, Any], field: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise VectorRailConsequenceCustodyPackageError(f"{field} must be non-empty")
    return result


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def main(argv: Sequence[str] | None = None) -> int:
    """Build/replay portable packages from a deterministic replay manifest."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to the replay manifest JSON")
    parser.add_argument("--output", type=Path, default=None, help="Optional output override")
    args = parser.parse_args(argv)

    result = execute_vectorrail_replay_manifest(args.manifest, output_path=args.output)
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


__all__ = [
    "VectorRailConsequenceCustodyPackageError",
    "VectorRailConsequenceCustodyPackageVerification",
    "build_vectorrail_consequence_custody_package",
    "execute_vectorrail_replay_manifest",
    "package_digest",
    "package_preimage",
    "verify_vectorrail_consequence_custody_package",
]


if __name__ == "__main__":
    raise SystemExit(main())
