from scripts.run_signatures_demo import main, make_demo_keypair, make_demo_tree_head, run_demo


def test_make_demo_keypair_is_deterministic() -> None:
    first = make_demo_keypair()
    second = make_demo_keypair()

    assert first == second
    assert len(first[0]) == 64
    assert len(first[1]) == 64


def test_make_demo_tree_head_is_synthetic() -> None:
    tree_head = make_demo_tree_head()

    assert tree_head.log_id == "ets-signature-demo"
    assert tree_head.signature is None


def test_run_demo_reports_signature_failures() -> None:
    result = run_demo()

    assert result["demo"] == "signatures"
    assert result["valid_signature"] is True
    assert result["tampered_signature"] is False
    assert result["wrong_signer"] is False


def test_main_prints_signature_demo_json(capsys) -> None:
    assert main() == 0

    output = capsys.readouterr().out
    assert '"demo": "signatures"' in output
    assert '"wrong_signer": false' in output
