"""Core ETS contracts and deterministic hashing helpers."""

from ets.core.artifacts import (
    ArtifactRecord,
    build_artifact_event_id,
    build_artifact_reference_uri,
    create_artifact_record,
    decode_artifact_base64,
    hash_artifact_bytes,
    normalize_artifact_metadata,
)
from ets.core.bundle import EvidenceProofBundle
from ets.core.canonical_json import canonical_sha256, canonicalize
from ets.core.federation import (
    FederationAssessment,
    FederationConflict,
    FederationObservation,
    assess_federation,
)
from ets.core.hash_chain import (
    GENESIS_BLOCK_HASH,
    ChainVerificationResult,
    HashChainBlock,
    build_block,
    export_block,
    recompute_block_hash,
    verify_chain,
)
from ets.core.log import DuplicateEventError, EventNotFoundError, InMemoryAppendOnlyLog, LogEntry
from ets.core.merkle import EMPTY_TREE_ROOT, audit_path_for_leaf, merkle_root
from ets.core.models import EvidenceEvent
from ets.core.proofs import (
    ConsistencyProof,
    InclusionProof,
    VerificationResult,
    generate_consistency_proof,
    generate_inclusion_proof,
)
from ets.core.quorum import QuorumDecision, VerifierVote, decide_quorum
from ets.core.sqlite_store import SQLiteEventStore
from ets.core.storage import EventStore, StorageValidationError
from ets.core.tree_head import SignedTreeHead

__all__ = [
    "EMPTY_TREE_ROOT",
    "ArtifactRecord",
    "DuplicateEventError",
    "EvidenceProofBundle",
    "EventNotFoundError",
    "EvidenceEvent",
    "EventStore",
    "ConsistencyProof",
    "FederationAssessment",
    "FederationConflict",
    "FederationObservation",
    "GENESIS_BLOCK_HASH",
    "ChainVerificationResult",
    "HashChainBlock",
    "InMemoryAppendOnlyLog",
    "InclusionProof",
    "LogEntry",
    "QuorumDecision",
    "SQLiteEventStore",
    "SignedTreeHead",
    "StorageValidationError",
    "VerificationResult",
    "VerifierVote",
    "audit_path_for_leaf",
    "assess_federation",
    "build_artifact_event_id",
    "build_artifact_reference_uri",
    "build_block",
    "canonical_sha256",
    "canonicalize",
    "create_artifact_record",
    "decode_artifact_base64",
    "export_block",
    "decide_quorum",
    "generate_consistency_proof",
    "generate_inclusion_proof",
    "hash_artifact_bytes",
    "merkle_root",
    "normalize_artifact_metadata",
    "recompute_block_hash",
    "verify_chain",
]
