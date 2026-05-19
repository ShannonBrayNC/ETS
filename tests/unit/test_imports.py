def test_sprint_00_packages_import():
    import ets.api
    import ets.core
    import ets.verifier

    assert ets.core.EvidenceEvent is not None
