from scripts.run_evidence_demo import encode_artifact, main, run_demo


def test_encode_artifact_returns_base64() -> None:
    assert encode_artifact(b"demo") == "ZGVtbw=="


def test_run_demo_reports_valid_and_tampered_artifact_results() -> None:
    result = run_demo()

    assert result["demo"] == "evidence-registration"
    assert result["valid_artifact"]["valid"] is True
    assert result["tampered_artifact"]["valid"] is False
    assert result["proof_event_id"] == "artifact_registered:artifact_demo_001"


def test_main_prints_evidence_demo_json(capsys) -> None:
    assert main() == 0

    output = capsys.readouterr().out
    assert '"demo": "evidence-registration"' in output
    assert '"tampered_artifact"' in output
