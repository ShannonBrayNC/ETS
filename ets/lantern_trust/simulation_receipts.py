from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel


class SimulationTrustReceipt(BaseModel):
    receipt_id: str
    scenario_id: str
    simulation_hash: str
    verifier: str
    verified_utc: str


def issue_simulation_receipt(
    scenario_id: str,
    simulation_hash: str,
    verifier: str,
) -> SimulationTrustReceipt:
    return SimulationTrustReceipt(
        receipt_id=str(uuid4()),
        scenario_id=scenario_id,
        simulation_hash=simulation_hash,
        verifier=verifier,
        verified_utc=datetime.now(UTC).isoformat(),
    )
