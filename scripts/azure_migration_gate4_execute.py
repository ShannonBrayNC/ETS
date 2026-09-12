#!/usr/bin/env python3
"""Gate 4 protected destination restore execution controller.

This module intentionally exposes no CLI.  It coordinates the separately reviewed
resumable Table suffix writer and rollback-first Gateway snapshot writer behind one
additional authorization boundary.  Runtime invocation is provided only by the
separately reviewed protected workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.azure_migration_control import MigrationControlError
from scripts.azure_migration_gate4_gateway_writer import (
    AUTHORIZATION_PHRASE as GATEWAY_AUTHORIZATION_PHRASE,
    apply_gateway_snapshot,
)
from scripts.azure_migration_gate4_suffix_writer import (
    AUTHORIZATION_PHRASE as SUFFIX_AUTHORIZATION_PHRASE,
    apply_resumable_suffix,
)

AUTHORIZATION_PHRASE = "GATE4_PROTECTED_TRANSFER_AUTHORIZED"


def execute_gate4_restore(
    workspace: Path,
    expected_manifest_sha256: str,
    expected_subscription: str,
    rollback_workspace: Path,
    authorization: str,
) -> dict[str, Any]:
    """Apply the reviewed Gate-4 Table suffix and Gateway snapshot sequence.

    The Table suffix is applied first because it is resumable and independently
    verifies the complete destination Table before returning.  The Gateway writer
    then captures a rollback snapshot before its first mutation and verifies exact
    durable-byte equivalence before returning.  Neither writer activates replicas,
    changes source state, changes RBAC, or performs cutover.
    """
    if authorization != AUTHORIZATION_PHRASE:
        raise MigrationControlError(
            "Gate 4 protected-transfer authorization phrase is missing"
        )

    table_result = apply_resumable_suffix(
        workspace=workspace,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_subscription=expected_subscription,
        authorization=SUFFIX_AUTHORIZATION_PHRASE,
    )

    gateway_result = apply_gateway_snapshot(
        workspace=workspace,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_subscription=expected_subscription,
        rollback_workspace=rollback_workspace,
        authorization=GATEWAY_AUTHORIZATION_PHRASE,
    )

    return {
        "table_destination_start_next_index": table_result[
            "destination_start_next_index"
        ],
        "table_source_next_index": table_result["source_next_index"],
        "table_suffix_entities_inserted": table_result[
            "suffix_entities_inserted"
        ],
        "table_staged_entities_reused": table_result["staged_entities_reused"],
        "table_metadata_updated": table_result["metadata_updated"],
        "table_write_performed": table_result["destination_write_performed"],
        "gateway_rollback_files_captured": gateway_result[
            "rollback_files_captured"
        ],
        "gateway_rollback_bytes_captured": gateway_result[
            "rollback_bytes_captured"
        ],
        "gateway_durable_files_overwritten": gateway_result[
            "durable_files_overwritten"
        ],
        "gateway_sidecars_removed": gateway_result["sidecars_removed"],
        "gateway_files_verified": gateway_result["gateway_files_verified"],
        "gateway_write_performed": gateway_result["gateway_write_performed"],
        "destination_prefix_replaced": False,
        "writer_activation_performed": False,
        "source_mutation_performed": False,
        "rbac_change_performed": False,
        "cutover_performed": False,
    }
