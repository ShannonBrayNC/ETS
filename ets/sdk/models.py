"""Stable application-facing ETS SDK contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ets.core import SignedTreeHead


class StrictSDKModel(BaseModel):
    """Strict immutable base for public application SDK contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SDKCompatibilityV1(StrictSDKModel):
    """Machine-readable compatibility declaration for ETS Application SDK v1."""

    schema_version: Literal["ets.sdk.compatibility.v1"] = "ets.sdk.compatibility.v1"
    sdk_contract: Literal["ets.application.sdk.v1"] = "ets.application.sdk.v1"
    api_versions: tuple[str, ...] = ("v1",)
    evidence_event_versions: tuple[str, ...] = ("ets.event.v1",)
    capture_versions: tuple[str, ...] = ("ets.capture.v1",)
    proof_bundle_versions: tuple[str, ...] = ("ets.proof_bundle.v1",)
    verifier_contracts: tuple[str, ...] = ("ets.verifier.v1",)
    connector_contracts: tuple[str, ...] = ("ets.connector.sdk.v1",)


class EventCommitReceiptV1(StrictSDKModel):
    """Receipt proving only that an event was committed to the returned local log view."""

    schema_version: Literal["ets.sdk.event_commit_receipt.v1"] = (
        "ets.sdk.event_commit_receipt.v1"
    )
    event_id: str = Field(min_length=1, max_length=128)
    log_index: int = Field(ge=0)
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_head: SignedTreeHead
    inclusion_proof_url: str = Field(min_length=1, max_length=4096)
    commitment_state: Literal["committed_local"] = "committed_local"


APPLICATION_SDK_COMPATIBILITY_V1 = SDKCompatibilityV1()
