"""Offline regression tests: every Azure command is intercepted by a fake CLI."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/hosted-azure-q1-resource-reaper.yml"
PRE = "Verify protected resource groups before cleanup"
CLEANUP = "Identify and remove stale synthetic Q1 groups"
POST = "Verify protected resource groups still exist"


def step_body(name: str) -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split(f"      - name: {name}\n", 1)[1].split("      - name:", 1)[0]
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


class ResourceReaperWorkflowTests(unittest.TestCase):
    def run_cleanup(self, replies: dict[str, str], groups: list[dict], dry_run: str = "false"):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            cli = directory / "az"
            cli.write_text(
                """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:2] == ["group", "exists"]:
    group = args[args.index("--name") + 1]
    reply = json.loads(os.environ["REPLIES"])[group]
    if reply == "Forbidden":
        print("ERROR: Operation returned an invalid status 'Forbidden'", file=sys.stderr)
        sys.exit(1)
    print(reply)
elif args[:2] == ["group", "list"]:
    print(os.environ["FIXTURE_GROUPS"])
elif args[:2] != ["group", "delete"]:
    sys.exit("Unexpected Azure operation")
""",
                encoding="utf-8",
            )
            cli.chmod(0o755)
            log = directory / "calls.jsonl"
            environment = dict(
                os.environ,
                PATH=str(directory) + os.pathsep + os.environ["PATH"],
                CALL_LOG=str(log),
                REPLIES=json.dumps(replies),
                FIXTURE_GROUPS=json.dumps(groups),
                EVENT_NAME="workflow_dispatch",
                MANUAL_DRY_RUN=dry_run,
                MANUAL_MAX_AGE_HOURS="24",
            )
            # GitHub's default success condition skips cleanup when the preflight fails.
            result = subprocess.run(
                ["bash", "-c", step_body(PRE)],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["bash", "-c", step_body(CLEANUP)],
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            return result, calls

    def test_gate_is_mandatory_before_cleanup_and_postcheck_remains(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertLess(text.index(PRE), text.index(CLEANUP))
        self.assertLess(text.index(CLEANUP), text.index(POST))
        pre = text.split(f"      - name: {PRE}", 1)[1].split("      - name:", 1)[0]
        cleanup = text.split(f"      - name: {CLEANUP}", 1)[1].split("      - name:", 1)[0]
        for section in (pre, cleanup):
            self.assertNotIn("continue-on-error:", section)
            self.assertNotIn("if:", section)
        self.assertIn("if: always()", text.split(f"      - name: {POST}", 1)[1])
        self.assertIn("rg-ets-q1-eastus rg-ets-live-eastus2", step_body(PRE))
        self.assertIn("rg-ets-q1-eastus rg-ets-live-eastus2", step_body(POST))

    def test_unverified_group_blocks_all_listing_and_deletion(self):
        eligible = [
            {
                "name": "rg-ets-q1-live-20000101000000",
                "tags": {"etsQualification": "HOST-AZ-Q1", "syntheticOnly": "true"},
            }
        ]
        for group in ("rg-ets-q1-eastus", "rg-ets-live-eastus2"):
            for failure in ("Forbidden", "false", "", "unexpected"):
                with self.subTest(group=group, failure=failure):
                    replies = dict.fromkeys(("rg-ets-q1-eastus", "rg-ets-live-eastus2"), "true")
                    replies[group] = failure
                    result, calls = self.run_cleanup(replies, eligible)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(all(call[:2] == ["group", "exists"] for call in calls))
                    self.assertIn(group, result.stderr)

    def test_existing_eligibility_guards_and_dry_run_are_preserved(self):
        tags = {"etsQualification": "HOST-AZ-Q1", "syntheticOnly": "true"}
        eligible = "rg-ets-q1-live-20000101000000"
        groups = [
            {"name": name, "tags": tags}
            for name in (
                eligible,
                "rg-ets-q1-eastus",
                "rg-ets-live-eastus",
                "rg-ets-live-eastus2",
                "rg-unrelated",
                "rg-ets-q1-live-29990101000000",
            )
        ]
        groups += [
            {"name": "rg-ets-q1-live-20000101000100", "tags": {}},
            {
                "name": "rg-ets-q1-live-20000101000200",
                "tags": {"etsQualification": "HOST-AZ-Q1", "syntheticOnly": "false"},
            },
        ]
        replies = dict.fromkeys(("rg-ets-q1-eastus", "rg-ets-live-eastus2"), "true")
        for dry_run in ("false", "true"):
            with self.subTest(dry_run=dry_run):
                result, calls = self.run_cleanup(replies, groups, dry_run)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    [call[:2] for call in calls[:3]],
                    [["group", "exists"], ["group", "exists"], ["group", "list"]],
                )
                deleted = [call for call in calls if call[:2] == ["group", "delete"]]
                self.assertEqual(
                    deleted,
                    []
                    if dry_run == "true"
                    else [["group", "delete", "--name", eligible, "--yes", "--no-wait"]],
                )


if __name__ == "__main__":
    unittest.main()
