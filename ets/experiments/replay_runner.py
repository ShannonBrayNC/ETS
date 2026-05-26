"""Deterministic replay-oriented experiment harness for ETS reproducibility research."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ets.benchmarks.run_benchmarks import run_benchmarks

DEFAULT_MANIFEST = Path("experiments/scenarios/sprint11-replay-manifest.json")
DEFAULT_OUTPUT = Path("artifacts/experiments")


def execute_manifest(
    manifest_path: Path = DEFAULT_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = []

    for scenario in manifest["scenarios"]:
        benchmark_result = run_benchmarks(
            output_dir=output_dir / scenario["id"],
            event_count=scenario["eventCount"],
        )

        scenarios.append(
            {
                "id": scenario["id"],
                "type": scenario["type"],
                "expectedResult": scenario["expectedResult"],
                "metrics": benchmark_result,
            }
        )

    result = {
        "manifest": manifest["name"],
        "seed": manifest["seed"],
        "scenarioCount": len(scenarios),
        "scenarios": scenarios,
    }

    (output_dir / "experiment-results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    (output_dir / "experiment-results.md").write_text(
        "\n".join(
            [
                "# ETS Experiment Results",
                "",
                f"- Manifest: {manifest['name']}",
                f"- Seed: {manifest['seed']}",
                f"- Scenarios: {len(scenarios)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return result


def main() -> int:
    result = execute_manifest()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
