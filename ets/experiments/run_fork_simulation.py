"""CLI entry point for fork simulation."""

from __future__ import annotations

import json

from ets.experiments.fork_simulation import run_fork_simulation


def main() -> int:
    print(json.dumps(run_fork_simulation().__dict__, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
