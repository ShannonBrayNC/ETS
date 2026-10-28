"""Behavioral checks for bounded setup retries, using only the standard library."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / 'scripts/ci-retry.sh'


@unittest.skipUnless(sys.platform != 'win32' and shutil.which('timeout'), 'GNU timeout required')
class RetryTests(unittest.TestCase):
    def run_retry(self, attempts, seconds, program, *arguments):
        return subprocess.run(
            ['bash', str(SCRIPT), str(attempts), str(seconds), '0', sys.executable,
             '-c', program, *arguments], capture_output=True, text=True, timeout=15)

    def test_transient_failure_recovers_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'attempts')
            result = self.run_retry(3, 2,
                'import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                'n=int(p.read_text())+1 if p.exists() else 1; '
                'p.write_text(str(n)); sys.exit(7 if n<2 else 0)', state)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(state).read_text(), '2')

    def test_permanent_failure_retains_exit_status(self):
        result = self.run_retry(3, 2, 'import sys; sys.exit(7)')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stderr.count('failed with exit 7'), 3)

    def test_hung_setup_is_bounded(self):
        result = self.run_retry(2, 1, 'import time; time.sleep(60)')
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stderr.count('failed with exit 124'), 2)

    def test_invalid_attempt_count_does_not_run(self):
        result = self.run_retry(0, 1, 'print("unexpected")')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('unexpected', result.stdout)
