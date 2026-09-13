# adaptive_programming/test_engine.py
"""
Test execution engine — runs tests and captures structured results.
"""
import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

# ULTRON_REPO_ROOT lets a sandboxed copy of this package keep targeting the real
# repository for benchmark verification (sandbox isolation support).
REPO_ROOT = Path(__file__).resolve().parent.parent
import os as _os
if _os.environ.get("ULTRON_REPO_ROOT"):
    REPO_ROOT = Path(_os.environ["ULTRON_REPO_ROOT"])


class TestResult:
    """Structured outcome of a test run."""

    def __init__(self, command: str):
        self.command = command
        self.run_id = f"test_{uuid.uuid4().hex[:8]}"
        self.returncode = -1
        self.stdout = ""
        self.stderr = ""
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.duration_sec = 0.0
        self.success = False

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "command": self.command,
            "returncode": self.returncode,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "duration_sec": round(self.duration_sec, 2),
            "success": self.success,
        }


class TestEngine:
    """Execute tests and parse results."""

    def __init__(self, root: Optional[Path] = None):
        self.root = (root or REPO_ROOT).resolve()

    def run_command(self, cmd: str, timeout: int = 120) -> TestResult:
        """Run an arbitrary test command and capture output."""
        result = TestResult(cmd)
        start = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.root,
            )
            result.returncode = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            self._parse_pytest_output(result)
        except subprocess.TimeoutExpired:
            result.stderr = f"Command timed out after {timeout}s"
            logger.error("Test command timed out: %s", cmd)
        except Exception as e:
            result.stderr = str(e)
            logger.error("Test command failed: %s — %s", cmd, e)

        result.duration_sec = time.perf_counter() - start
        result.success = result.returncode == 0 and result.failed == 0 and result.errors == 0
        return result

    def run_pytest(self, target: str = "backend/tests", timeout: int = 180) -> TestResult:
        """Run pytest on a target path."""
        return self.run_command(f"py -m pytest {target} -x -q --tb=short 2>&1", timeout=timeout)

    def run_single_test(self, test_path: str, timeout: int = 60) -> TestResult:
        """Run a single test file or test function."""
        return self.run_command(f"py -m pytest {test_path} -x -q --tb=long 2>&1", timeout=timeout)

    def _parse_pytest_output(self, result: TestResult) -> None:
        """Parse pytest summary line for pass/fail/error counts."""
        output = result.stdout + result.stderr
        # Match patterns like "5 passed, 2 failed, 1 error" or "1 passed"
        import re
        passed_m = re.search(r"(\d+)\s+passed", output)
        failed_m = re.search(r"(\d+)\s+failed", output)
        error_m = re.search(r"(\d+)\s+error", output)

        if passed_m:
            result.passed = int(passed_m.group(1))
        if failed_m:
            result.failed = int(failed_m.group(1))
        if error_m:
            result.errors = int(error_m.group(1))

    def parse_failures(self, output: str) -> List[Dict]:
        """Extract structured failure details from pytest output."""
        failures = []
        import re
        # Capture FAILED lines
        for match in re.finditer(r"FAILED\s+([^\s]+)\s*-\s*(.+)", output):
            failures.append({
                "test": match.group(1),
                "message": match.group(2).strip(),
            })
        # Capture ERROR lines
        for match in re.finditer(r"ERROR\s+([^\s]+)\s*-\s*(.+)", output):
            failures.append({
                "test": match.group(1),
                "message": match.group(2).strip(),
                "type": "error",
            })
        return failures
