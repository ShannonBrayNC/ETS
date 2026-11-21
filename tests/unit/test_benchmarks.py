import json

import pytest

from ets.benchmarks.run_benchmarks import run_benchmarks


def test_benchmark_writes_json_and_markdown(tmp_path) -> None:
    result = run_benchmarks(tmp_path, event_count=5, proof_sample_count=7)

    json_path = tmp_path / "benchmark-results.json"
    md_path = tmp_path / "benchmark-results.md"
    assert json_path.exists()
    assert md_path.exists()
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "ets.benchmark_results.v2"
    assert persisted["event_count"] == 5
    assert persisted["proof_sample_count"] == 7
    assert result["tree_size"] == 5
    metrics = persisted["metrics"]
    assert metrics["append"]["latency_ms"]["samples"] == 5
    assert metrics["inclusion_proof_generation"]["latency_ms"]["samples"] == 7
    assert metrics["inclusion_proof_verification"]["latency_ms"]["samples"] == 7
    assert metrics["proof_size_bytes"]["samples"] == 7
    assert 0 <= metrics["append"]["latency_ms"]["p50"]
    assert (
        metrics["inclusion_proof_generation"]["latency_ms"]["p50"]
        <= metrics["inclusion_proof_generation"]["latency_ms"]["p95"]
        <= metrics["inclusion_proof_generation"]["latency_ms"]["p99"]
    )

    markdown = md_path.read_text(encoding="utf-8")
    assert "Inclusion proof verification" in markdown
    assert "machine-dependent" in markdown
    assert "not production throughput" in markdown


@pytest.mark.parametrize(
    ("event_count", "proof_sample_count", "message"),
    [
        (0, 1, "event_count must be at least 1"),
        (1, 0, "proof_sample_count must be at least 1"),
    ],
)
def test_benchmark_rejects_empty_workloads(
    tmp_path, event_count: int, proof_sample_count: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        run_benchmarks(tmp_path, event_count, proof_sample_count)
