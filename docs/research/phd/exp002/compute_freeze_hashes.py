#!/usr/bin/env python3
"""Compute deterministic SHA-256 values for the frozen EXP-002 input artifacts.

Run from any working directory in a clean checkout of the final merged research commit.
This utility does not modify the experiment artifacts.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ARTIFACTS = [
    "EA_CONDITION_SCHEMA.json",
    "EQUIVALENCE_RUBRIC.md",
    "NORMALIZED_CONCLUSION_SCHEMA.json",
    "RATS_BASELINE_ADVERSARIAL_REVIEW.md",
    "RATS_CONDITION_SCHEMA.json",
    "SCENARIO_CORPUS.json",
    "SEMANTIC_VOCABULARY.md",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=HERE, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNAVAILABLE"


def main() -> int:
    missing = [name for name in ARTIFACTS if not (HERE / name).is_file()]
    if missing:
        print("Missing frozen artifacts:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        return 2

    commit = git_value("rev-parse", "HEAD")
    worktree = git_value("status", "--porcelain")
    print(f"commit_sha={commit}")
    print(f"working_tree_clean={'true' if worktree == '' else 'false'}")
    print("sha256:")
    for name in ARTIFACTS:
        path = HERE / name
        print(f"{sha256_file(path)}  {name}")

    if worktree not in ("", "UNAVAILABLE"):
        print(
            "WARNING: working tree is not clean; do not use these values "
            "as the final execution freeze.",
            file=sys.stderr,
        )
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
