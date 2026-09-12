#!/usr/bin/env python3
"""Compute SHA-256 values for frozen EXP-003 pre-execution artifacts."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ARTIFACTS = [
    "BASELINE_PROFILE.json",
    "CONSEQUENCE_MODEL.json",
    "EPISTEMIC_STATES.json",
    "EXP003NonCollapse.tla",
    "FACT_GRAMMAR.json",
    "INDEPENDENCE_MODEL.json",
    "NON_COLLAPSE_RULES.json",
    "PROPOSITION_SCHEMA.json",
    "analysis_skeleton.py",
    "condition_a.py",
    "condition_b.py",
    "condition_c_rats_plus.py",
    "generator.py",
    "oracle.py",
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
    except (OSError, subprocess.SubprocessError):
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
    print(f"python={platform.python_version()}")
    print(f"platform={platform.platform()}")
    print("sha256:")
    for name in ARTIFACTS:
        print(f"{sha256_file(HERE / name)}  {name}")

    if worktree not in ("", "UNAVAILABLE"):
        warning = "WARNING: working tree is not clean; do not use values as final freeze."
        print(warning, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
