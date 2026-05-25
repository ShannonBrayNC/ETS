"""Lantern cross-application trust verification helpers.

This package lets ETS act as a trust anchor for governance events flowing between
SignalForge, Christina, OpsHelm, and future Lantern applications.
"""

from ets.lantern_trust.contracts import LanternGovernanceEvent, LanternTrustReceipt
from ets.lantern_trust.verifier import verify_receipt

__all__ = ["LanternGovernanceEvent", "LanternTrustReceipt", "verify_receipt"]
