"""Compatibility facade for ETS Core.

New integrations should import from :mod:`ets.core.api`. Historical package-level
exports remain available through lazy resolution so importing ``ets.core`` or
``ets.core.api`` does not initialize storage, hosting, federation, or reporting
components.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "EMPTY_TREE_ROOT": ("ets.core.merkle", "EMPTY_TREE_ROOT"),
    "ArtifactRecord": ("ets.core.artifacts", "ArtifactRecord"),
    "ArtifactRegistryError": ("ets.core.artifact_registry", "ArtifactRegistryError"),
    "AnchorExport": ("ets.core.anchors", "AnchorExport"),
    "AnchorTarget": ("ets.core.anchors", "AnchorTarget"),
    "AnchorVerificationResult": ("ets.core.anchors", "AnchorVerificationResult"),
    "DuplicateEventError": ("ets.core.log", "DuplicateEventError"),
    "EvidenceProofBundle": ("ets.core.bundle", "EvidenceProofBundle"),
    "EventNotFoundError": ("ets.core.log", "EventNotFoundError"),
    "EvidenceEvent": ("ets.core.models", "EvidenceEvent"),
    "EventStore": ("ets.core.storage", "EventStore"),
    "ConsistencyProof": ("ets.core.proofs", "ConsistencyProof"),
    "FederationAssessment": ("ets.core.federation", "FederationAssessment"),
    "FederationConflict": ("ets.core.federation", "FederationConflict"),
    "FederationObservation": ("ets.core.federation", "FederationObservation"),
    "GENESIS_BLOCK_HASH": ("ets.core.hash_chain", "GENESIS_BLOCK_HASH"),
    "ChainVerificationResult": ("ets.core.hash_chain", "ChainVerificationResult"),
    "HashChainBlock": ("ets.core.hash_chain", "HashChainBlock"),
    "InMemoryAppendOnlyLog": ("ets.core.log", "InMemoryAppendOnlyLog"),
    "InclusionProof": ("ets.core.proofs", "InclusionProof"),
    "LogEntry": ("ets.core.log", "LogEntry"),
    "QuorumDecision": ("ets.core.quorum", "QuorumDecision"),
    "SQLiteEventStore": ("ets.core.sqlite_store", "SQLiteEventStore"),
    "SignedTreeHead": ("ets.core.tree_head", "SignedTreeHead"),
    "StorageValidationError": ("ets.core.storage", "StorageValidationError"),
    "VerificationResult": ("ets.core.proofs", "VerificationResult"),
    "VerifierVote": ("ets.core.quorum", "VerifierVote"),
    "artifact_record_from_log_entry": ("ets.core.artifact_registry", "artifact_record_from_log_entry"),
    "audit_path_for_leaf": ("ets.core.merkle", "audit_path_for_leaf"),
    "anchor_export_payload": ("ets.core.anchors", "anchor_export_payload"),
    "assess_federation": ("ets.core.federation", "assess_federation"),
    "build_artifact_event_id": ("ets.core.artifacts", "build_artifact_event_id"),
    "build_artifact_reference_uri": ("ets.core.artifacts", "build_artifact_reference_uri"),
    "build_block": ("ets.core.hash_chain", "build_block"),
    "build_anchor_export": ("ets.core.anchors", "build_anchor_export"),
    "canonical_sha256": ("ets.core.canonical_json", "canonical_sha256"),
    "canonicalize": ("ets.core.canonical_json", "canonicalize"),
    "create_artifact_record": ("ets.core.artifacts", "create_artifact_record"),
    "decode_artifact_base64": ("ets.core.artifacts", "decode_artifact_base64"),
    "export_block": ("ets.core.hash_chain", "export_block"),
    "decide_quorum": ("ets.core.quorum", "decide_quorum"),
    "generate_consistency_proof": ("ets.core.proofs", "generate_consistency_proof"),
    "generate_inclusion_proof": ("ets.core.proofs", "generate_inclusion_proof"),
    "hash_artifact_bytes": ("ets.core.artifacts", "hash_artifact_bytes"),
    "load_artifact_registry": ("ets.core.artifact_registry", "load_artifact_registry"),
    "merkle_root": ("ets.core.merkle", "merkle_root"),
    "normalize_artifact_metadata": ("ets.core.artifacts", "normalize_artifact_metadata"),
    "recompute_block_hash": ("ets.core.hash_chain", "recompute_block_hash"),
    "verify_chain": ("ets.core.hash_chain", "verify_chain"),
    "verify_anchor_export": ("ets.core.anchors", "verify_anchor_export"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> object:
    """Resolve historical exports only when a consumer requests them."""

    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose compatibility names to interactive tooling without importing them."""

    return sorted([*globals(), *__all__])
