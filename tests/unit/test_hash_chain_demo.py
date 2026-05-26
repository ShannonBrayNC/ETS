from scripts.run_hash_chain_demo import main, make_demo_event, run_demo


def test_make_demo_event_uses_synthetic_non_pii_metadata() -> None:
    event = make_demo_event("evt_demo_001", "a" * 64)

    assert event.event_id == "evt_demo_001"
    assert event.metadata["contains_real_pii"] is False


def test_run_demo_reports_valid_and_tampered_chain_results() -> None:
    result = run_demo()

    assert result["demo"] == "hash-chain"
    assert result["valid_chain"]["valid"] is True
    assert result["tampered_chain"]["valid"] is False
    assert result["tampered_chain"]["reason"] == "previous block hash does not match"


def test_main_prints_demo_json(capsys) -> None:
    assert main() == 0

    output = capsys.readouterr().out
    assert '"demo": "hash-chain"' in output
    assert '"tampered_chain"' in output
