"""Stable application-facing ETS SDK contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ets.core import EvidenceEvent, SignedTreeHead


class StrictSDKModel(BaseModel):
    """Strict immutable base for public application SDK contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SDKWireModel(BaseModel):
    """Forward-compatible immutable model for API responses."""

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)


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


class ServiceHealthV1(SDKWireModel):
    """Public health response returned by ETS."""

    status: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)


class ServiceVersionV1(SDKWireModel):
    """Public ETS service version response."""

    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    api_version: str = Field(min_length=1, max_length=100)


class EventRecordV1(SDKWireModel):
    """Committed event record returned by the ETS API."""

    log_index: int = Field(ge=0)
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    leaf_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event: EvidenceEvent


class EventPageV1(SDKWireModel):
    """Bounded page of committed ETS events."""

    items: list[EventRecordV1]
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


APPLICATION_SDK_COMPATIBILITY_V1 = SDKCompatibilityV1()
