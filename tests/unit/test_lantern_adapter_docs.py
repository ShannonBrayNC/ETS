from pathlib import Path


def test_lantern_adapter_contract_covers_required_handoffs() -> None:
    document = Path("docs/lantern-adapter.md").read_text(encoding="utf-8")

    required_terms = [
        "Ticket ingestion",
        "Log and HAR analysis",
        "Customer update drafting",
        "Escalation recommendation",
        "ROI and time-saved calculation",
        "Report export",
        "Input payload from Lantern Core",
        "Output artifacts to Lantern Core",
        "memoryObservations",
        "Content Engine handoff",
        "Human approval required",
    ]

    for term in required_terms:
        assert term in document
