from scripts.run_anchor_demo import make_demo_event, run_demo


def test_make_demo_event_uses_synthetic_metadata():
    event = make_demo_event(1)

    assert event["event_id"] == "evt_anchor_001"
    assert event["metadata"]["contains_real_pii"] is False


def test_anchor_demo_exports_verifies_and_rejects_tamper():
    result = run_demo()

    assert result["demo"] == "external-anchor"
    assert result["target"] == "github_release"
    assert result["tree_size"] == 3
    assert result["history_count"] == 1
    assert result["verified_anchor"]["valid"] is True
    assert result["tampered_anchor"]["valid"] is False
    assert result["tampered_anchor"]["reason"] == "merkle root does not match tree head"
