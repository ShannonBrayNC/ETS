"""Runner-local report paths must be initialized only after a runner is assigned."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
STEP = "      - name: Initialize runner-local report paths\n"
EXPECTED = {
    "azure-migration-gate9b-source-retirement-execute.yml": [
        {
            "GATE9_DIR": "/gate9-readiness",
            "INVENTORY_DIR": "/gate9b-inventory",
            "GATE9_REPORT": "/gate9-readiness/ets-gate9-decommission-readiness.json",
            "INVENTORY_REPORT": "/gate9b-inventory/ets-gate9b-source-retirement-inventory.json",
            "RETIREMENT_RESULT": "/ets-gate9b-source-retirement-execution.json",
        },
        {
            "RETIREMENT_DIR": "/gate9b-retirement",
            "RETIREMENT_REPORT": "/gate9b-retirement/ets-gate9b-source-retirement-execution.json",
            "ACTIVE_PROBE_REPORT": "/ets-gate9b-active-gateway-probe.json",
            "M365_MARKER": "/ets-gate9b-m365-marker.json",
            "PUBLIC_MARKER": "/ets-gate9b-public-marker.json",
            "FINAL_REPORT": "/ets-gate9b-source-retirement-final.json",
        },
    ],
    "azure-migration-gate9b-source-retirement-inventory.yml": [
        {
            "GATE9_DIR": "/gate9-readiness",
            "GATE9_REPORT": "/gate9-readiness/ets-gate9-decommission-readiness.json",
            "INVENTORY_REPORT": "/ets-gate9b-source-retirement-inventory.json",
        },
    ],
}


class Gate9bReportPathsTests(unittest.TestCase):
    def test_paths_are_not_evaluated_in_job_env(self):
        for filename, expected_jobs in EXPECTED.items():
            with self.subTest(workflow=filename):
                text = (WORKFLOWS / filename).read_text()
                self.assertIsNone(re.search(r"^      \w+:.*runner\.temp", text, re.M))
                self.assertEqual(text.count("    steps:\n" + STEP), len(expected_jobs))

    def test_initialization_writes_exact_existing_paths_with_spaces(self):
        for filename, expected_jobs in EXPECTED.items():
            text = (WORKFLOWS / filename).read_text()
            sections = text.split(STEP)[1:]
            self.assertEqual(len(sections), len(expected_jobs))
            for section, expected in zip(sections, expected_jobs, strict=True):
                with self.subTest(workflow=filename, keys=tuple(expected)):
                    section = section.split("      - name:", 1)[0]
                    script = textwrap.dedent(section.split("        run: |\n", 1)[1])
                    with tempfile.TemporaryDirectory(prefix="runner with spaces ") as directory:
                        env_file = Path(directory) / "github env"
                        env_file.write_text("EXISTING=preserved\n")
                        result = subprocess.run(
                            ["bash", "-c", script],
                            env=dict(os.environ, RUNNER_TEMP=directory, GITHUB_ENV=str(env_file)),
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        values = dict(
                            line.split("=", 1) for line in env_file.read_text().splitlines()
                        )
                        self.assertEqual(values.pop("EXISTING"), "preserved")
                        self.assertEqual(values, {k: directory + v for k, v in expected.items()})
                        self.assertEqual(list(Path(directory).iterdir()), [env_file])


if __name__ == "__main__":
    unittest.main()
