import json

from ets.benchmarks.run_benchmarks import run_benchmarks


def test_benchmark_writes_json_and_markdown(tmp_path) -> None:
    result = run_benchmarks(tmp_path, event_count=5)

    json_path = tmp_path / "benchmark-results.json"
    md_path = tmp_path / "benchmark-results.md"
    assert json_path.exists()
    assert md_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["event_count"] == 5
    assert result["tree_size"] == 5
