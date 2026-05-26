from scripts.run_phase2_demo import run_demo as run_phase2_demo
from scripts.run_phase3_demo import run_demo as run_phase3_demo


def test_phase2_demo_covers_enterprise_explorer_story() -> None:
    result = run_phase2_demo()

    assert result["demo"] == "phase2-enterprise-explorer"
    assert result["verification"]["valid"] is True
    assert result["tamperSimulation"]["valid"] is False
    assert result["tamperSimulation"]["reason"] == "content hash mismatch"
    assert "Azure Storage immutable blob policies for evidence/proof exports" in result["azurePath"]
    assert "signed tree head retrieval" in result["apiSurface"]
    assert result["steps"] == [
        "upload artifact",
        "generate proof",
        "view explorer timeline",
        "verify artifact",
        "simulate tampering",
        "display failed verification",
    ]


def test_phase3_demo_detects_divergent_node_history() -> None:
    result = run_phase3_demo()

    assert result["demo"] == "phase3-distributed-trust"
    assert result["synchronization"]["valid"] is True
    assert result["sharedEvidenceVerification"]["presentOnAllNodes"] is True
    assert result["divergenceReport"]["valid"] is False
    assert result["divergenceReport"]["divergentNodes"][0]["nodeId"] == "node-c"
    assert result["divergenceReport"]["divergentNodes"][0]["reason"] == "mismatched block root"
    assert "Local deterministic verifier federation demo" in result["note"]
