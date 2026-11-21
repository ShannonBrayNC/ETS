"""Generate bounded benchmark artifacts for ETS protocol operations."""

from __future__ import annotations

import json
import os
import platform
import statistics
import time
from pathlib import Path
from typing import TypedDict, cast

from ets.core import InMemoryAppendOnlyLog, generate_inclusion_proof
from ets.core.proofs import verify_inclusion_proof
from ets.experiments.dataset import generate_synthetic_events


class LatencySummary(TypedDict):
    samples: int
    min: float
    mean: float
    p50: float
    p95: float
    p99: float
    max: float


def run_benchmarks(
    output_dir: Path = Path("artifacts/benchmarks"),
    event_count: int = 100,
    proof_sample_count: int = 100,
) -> dict[str, object]:
    """Measure a synthetic in-memory append and inclusion-proof workload.

    The retained percentiles describe this process on this runner. They are not
    service-level objectives or production-capacity claims.
    """

    if event_count < 1:
        raise ValueError("event_count must be at least 1")
    if proof_sample_count < 1:
        raise ValueError("proof_sample_count must be at least 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    events = generate_synthetic_events(event_count)
    log = InMemoryAppendOnlyLog()

    append_latencies_ns: list[int] = []
    append_start_ns = time.perf_counter_ns()
    for event in events:
        operation_start_ns = time.perf_counter_ns()
        log.append(event)
        append_latencies_ns.append(time.perf_counter_ns() - operation_start_ns)
    append_elapsed_ns = time.perf_counter_ns() - append_start_ns

    entries = log.list_entries()
    generation_latencies_ns: list[int] = []
    verification_latencies_ns: list[int] = []
    proof_sizes_bytes: list[int] = []
    for leaf_index in _sample_leaf_indexes(event_count, proof_sample_count):
        operation_start_ns = time.perf_counter_ns()
        proof = generate_inclusion_proof(entries, leaf_index)
        generation_latencies_ns.append(time.perf_counter_ns() - operation_start_ns)

        operation_start_ns = time.perf_counter_ns()
        verification = verify_inclusion_proof(proof)
        verification_latencies_ns.append(time.perf_counter_ns() - operation_start_ns)
        if not verification.valid:
            raise RuntimeError(f"generated inclusion proof did not verify: {verification.reason}")

        proof_sizes_bytes.append(
            len(proof.model_dump_json(exclude_none=True).encode("utf-8"))
        )

    append_seconds = append_elapsed_ns / 1_000_000_000
    result: dict[str, object] = {
        "schema_version": "ets.benchmark_results.v2",
        "event_count": event_count,
        "tree_size": len(entries),
        "proof_sample_count": proof_sample_count,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "timer": "perf_counter_ns",
            "source_revision": os.getenv("GITHUB_SHA"),
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
        },
        "metrics": {
            "append": {
                "total_seconds": append_seconds,
                "events_per_second": event_count / append_seconds,
                "latency_ms": _summarize_ns(append_latencies_ns),
            },
            "inclusion_proof_generation": {
                "latency_ms": _summarize_ns(generation_latencies_ns),
            },
            "inclusion_proof_verification": {
                "latency_ms": _summarize_ns(verification_latencies_ns),
            },
            "proof_size_bytes": _summarize_values(proof_sizes_bytes),
        },
        "limitations": [
            "Synthetic non-PII events and an in-memory log only.",
            "Timings are machine-dependent bounded engineering measurements.",
            "Results are not a production throughput claim or service-level objective.",
        ],
    }
    (output_dir / "benchmark-results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "benchmark-results.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )
    return result


def _sample_leaf_indexes(event_count: int, sample_count: int) -> list[int]:
    """Return deterministic indexes spanning the complete tree."""

    if sample_count == 1:
        return [event_count - 1]
    return [
        sample_number * (event_count - 1) // (sample_count - 1)
        for sample_number in range(sample_count)
    ]


def _summarize_ns(samples_ns: list[int]) -> LatencySummary:
    return _summarize_values([sample / 1_000_000 for sample in samples_ns])


def _summarize_values(samples: list[int] | list[float]) -> LatencySummary:
    ordered = sorted(float(sample) for sample in samples)
    return {
        "samples": len(ordered),
        "min": ordered[0],
        "mean": statistics.fmean(ordered),
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
        "max": ordered[-1],
    }


def _percentile(ordered_samples: list[float], quantile: float) -> float:
    """Return a linearly interpolated percentile for already sorted samples."""

    position = (len(ordered_samples) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_samples) - 1)
    fraction = position - lower_index
    return ordered_samples[lower_index] + fraction * (
        ordered_samples[upper_index] - ordered_samples[lower_index]
    )


def _render_markdown(result: dict[str, object]) -> str:
    metrics = cast(dict[str, object], result["metrics"])
    rows: list[tuple[str, str, LatencySummary]] = []
    for key, label in (
        ("append", "Append latency"),
        ("inclusion_proof_generation", "Inclusion proof generation"),
        ("inclusion_proof_verification", "Inclusion proof verification"),
    ):
        metric = cast(dict[str, object], metrics[key])
        summary = cast(LatencySummary, metric["latency_ms"])
        rows.append((label, "ms", summary))

    proof_size = cast(LatencySummary, metrics["proof_size_bytes"])
    rows.append(("Serialized proof size", "bytes", proof_size))
    table_rows = [
        "| Metric | Unit | Samples | Mean | p50 | p95 | p99 | Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, unit, summary in rows:
        table_rows.append(
            f"| {label} | {unit} | {summary['samples']} | "
            f"{summary['mean']:.6f} | {summary['p50']:.6f} | "
            f"{summary['p95']:.6f} | {summary['p99']:.6f} | "
            f"{summary['max']:.6f} |"
        )

    environment = cast(dict[str, object], result["environment"])
    return "\n".join(
        [
            "# ETS Benchmark Results",
            "",
            f"- Schema: `{result['schema_version']}`",
            f"- Events/tree size: {result['event_count']}",
            f"- Proof samples: {result['proof_sample_count']}",
            f"- Python: {environment['implementation']} {environment['python']}",
            f"- Platform: {environment['platform']} ({environment['machine']})",
            f"- Source revision: {environment['source_revision'] or 'not recorded'}",
            f"- GitHub run: {environment['github_run_id'] or 'local'}",
            "",
            *table_rows,
            "",
            "## Interpretation boundary",
            "",
            "These are machine-dependent, bounded engineering measurements over synthetic",
            "events and the in-memory log. They are not production throughput, capacity,",
            "or service-level claims.",
            "",
        ]
    )


def main() -> int:
    result = run_benchmarks()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
