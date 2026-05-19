"""Generate lightweight benchmark artifacts for ETS protocol operations."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ets.core import InMemoryAppendOnlyLog, generate_inclusion_proof
from ets.experiments.dataset import generate_synthetic_events


def run_benchmarks(
    output_dir: Path = Path("artifacts/benchmarks"),
    event_count: int = 100,
) -> dict[str, float | int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    events = generate_synthetic_events(event_count)
    log = InMemoryAppendOnlyLog()

    start = time.perf_counter()
    for event in events:
        log.append(event)
    append_seconds = time.perf_counter() - start

    start = time.perf_counter()
    proof = generate_inclusion_proof(log.list_entries(), max(0, event_count - 1))
    proof_seconds = time.perf_counter() - start

    result: dict[str, float | int] = {
        "event_count": event_count,
        "append_seconds": append_seconds,
        "proof_seconds": proof_seconds,
        "tree_size": proof.tree_size,
    }
    (output_dir / "benchmark-results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "benchmark-results.md").write_text(
        "\n".join(
            [
                "# ETS Benchmark Results",
                "",
                f"- Events: {event_count}",
                f"- Append seconds: {append_seconds:.6f}",
                f"- Proof seconds: {proof_seconds:.6f}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    result = run_benchmarks()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
