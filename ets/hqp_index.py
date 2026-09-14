"""CLI for validating and rendering the HQP-5 qualification index."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ets.qualification.index import load_qualification_index, render_qualification_index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and render an ETS qualification index")
    parser.add_argument(
        "--index",
        type=Path,
        default=Path("docs/qualification/qualification-index.json"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    index = load_qualification_index(args.index.read_bytes())
    print(render_qualification_index(index), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
