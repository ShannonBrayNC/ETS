from pathlib import Path

from ets.desktop import host
from ets.desktop.developer_smoke import DeveloperSmoke


def test_developer_smoke_uses_only_private_picker_targets(tmp_path):
    scenario = DeveloperSmoke(tmp_path)
    assert Path(scenario.choose("sample_parent")) == tmp_path
    assert Path(scenario.choose("sdk_zip")).parent == tmp_path
    assert Path(scenario.choose("json")).parent == tmp_path
    assert scenario.choose("bundle") is None
    assert scenario.choose("trust") is None
    assert scenario.choose("unsupported") is None


def test_developer_smoke_launch_is_separate_and_temp_folder_removed(monkeypatch):
    observed = []

    def launch(smoke, scenario, *, developer, smoke_observations):
        assert smoke_observations == {}
        assert smoke and developer and isinstance(scenario, DeveloperSmoke)
        assert scenario.directory.is_dir()
        observed.append(scenario.directory)
        return 0

    monkeypatch.setattr("sys.argv", ["ets-developer", "--smoke-test"])
    monkeypatch.setattr(host, "_launch", launch)
    assert host.main(developer=True) == 0
    assert observed and not observed[0].exists()
