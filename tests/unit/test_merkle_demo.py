from scripts.run_merkle_demo import main, make_demo_event, run_demo


def test_make_demo_event_uses_synthetic_non_pii_metadata() -> None:
    event = make_demo_event(1)

    assert event.event_id == "evt_merkle_001"
    assert event.metadata["contains_real_pii"] is False


def test_run_demo_reports_valid_and_tampered_proof_results() -> None:
    result = run_demo()

    assert result["demo"] == "merkle-proof"
    assert result["valid_proof"]["valid"] is True
    assert result["tampered_proof"]["valid"] is False
    assert result["proof"]["tree_size"] == 4


def test_main_prints_merkle_demo_json(capsys) -> None:
    assert main() == 0

    output = capsys.readouterr().out
    assert '"demo": "merkle-proof"' in output
    assert '"tampered_proof"' in output
