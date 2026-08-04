"""Verify branch-protection runbook required checks against repo configuration."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/runbooks/branch-protection.md"
WORKFLOW_DIR = ROOT / ".github/workflows"
PROTECTION_API = "https://api.github.com/repos/ShannonBrayNC/ETS/branches/main/protection"


def read_required_contexts_from_runbook() -> list[str]:
    text = RUNBOOK.read_text(encoding="utf-8")
    match = re.search(
        r"## Required Checks\s+"
        r"The following checks are required before a pull request can merge into `main`:\s+"
        r"(?P<checks>(?:\s*-\s+`[^`]+`\s*)+)",
        text,
    )
    if not match:
        raise AssertionError(
            "Could not find the Required Checks list in the branch protection runbook."
        )

    return re.findall(r"-\s+`([^`]+)`", match.group("checks"))


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_workflow_check_contexts() -> set[str]:
    contexts: set[str] = set()
    job_header = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
    name_line = re.compile(r"^    name:\s*(.+?)\s*$")

    for workflow in sorted(WORKFLOW_DIR.glob("*.yml")):
        lines = workflow.read_text(encoding="utf-8").splitlines()
        in_jobs = False
        current_job: str | None = None
        current_name: str | None = None

        def flush_current() -> None:
            nonlocal current_job, current_name
            if current_job is not None:
                contexts.add(strip_quotes(current_name or current_job))
            current_job = None
            current_name = None

        for line in lines:
            if line == "jobs:":
                in_jobs = True
                continue
            if not in_jobs:
                continue
            if line and not line.startswith(" "):
                flush_current()
                in_jobs = False
                continue

            header = job_header.match(line)
            if header:
                flush_current()
                current_job = header.group(1)
                continue

            if current_job is not None:
                name = name_line.match(line)
                if name:
                    current_name = name.group(1)

        flush_current()

    return contexts


def read_live_required_contexts() -> list[str]:
    token = os.environ.get("GITHUB_TOKEN")
    request = urllib.request.Request(
        PROTECTION_API,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(
            f"Could not read live branch protection: HTTP {exc.code} {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AssertionError(f"Could not read live branch protection: {exc}") from exc

    return list(payload["required_status_checks"]["contexts"])


def assert_same(label: str, expected: list[str], actual: list[str]) -> None:
    if expected == actual:
        return

    expected_set = set(expected)
    actual_set = set(actual)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    ordered = expected != actual and not missing and not extra
    details = [f"{label} does not match docs/runbooks/branch-protection.md."]
    if missing:
        details.append(f"Missing: {', '.join(missing)}")
    if extra:
        details.append(f"Extra: {', '.join(extra)}")
    if ordered:
        details.append("The contexts match as a set but not in documented order.")
    details.append(f"Runbook: {expected}")
    details.append(f"{label}: {actual}")
    raise AssertionError("\n".join(details))


def main() -> int:
    runbook_contexts = read_required_contexts_from_runbook()
    workflow_contexts = read_workflow_check_contexts()
    missing_from_workflows = [
        context for context in runbook_contexts if context not in workflow_contexts
    ]
    if missing_from_workflows:
        raise AssertionError(
            "Required branch-protection contexts are not produced by workflow jobs: "
            + ", ".join(missing_from_workflows)
        )

    if os.environ.get("ETS_VERIFY_LIVE_BRANCH_PROTECTION") == "1":
        live_contexts = read_live_required_contexts()
        assert_same("Live branch protection", runbook_contexts, live_contexts)

    print("Branch protection runbook verification passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Branch protection runbook verification failed:\n{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
