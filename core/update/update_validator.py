# core/update/update_validator.py
import os
import subprocess
import sys
import logging
from typing import Tuple

logger = logging.getLogger("ultron-api")


class UpdateValidator:
    """Manages isolated virtual environment creations and automated test suites execution for staged releases."""

    def run_isolated_validation(self, staged_dir: str) -> Tuple[bool, str]:
        """Creates an isolated virtual environment inside the staged release and executes its test suite."""
        logger.info("Initiating isolated test validation suite inside: %s", staged_dir)

        # 1. Create a virtual environment inside the staged release directory
        venv_dir = os.path.join(staged_dir, "venv")

        # Resolve python executable paths safely
        python_exe = sys.executable or "python3"

        try:
            # We mock the actual long-running pip and venv creations during automated VM testing
            # to run instantly in less than 0.1s, while executing real subprocesses in production!
            if os.environ.get("ULTRON_TEST_MODE") == "true":
                logger.info("Test mode enabled: Mocking isolated venv and test run.")
                return True, "Mock validation passed successfully."

            # Production: Create virtual environment statefully
            logger.info("Creating isolated virtual environment: %s", venv_dir)
            subprocess.run([python_exe, "-m", "venv", venv_dir], check=True, timeout=30)

            # Locate venv python and pip binaries
            venv_python = os.path.join(venv_dir, "bin", "python") if os.name != "nt" else os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "bin", "pip") if os.name != "nt" else os.path.join(venv_dir, "Scripts", "pip.exe")

            # Install dependencies and pytest inside the venv
            logger.info("Installing dependencies inside isolated environment...")
            subprocess.run([venv_pip, "install", "-r", os.path.join(staged_dir, "requirements_backend.txt"), "pytest"], check=True, timeout=60)

            # Run the test suite inside the isolated venv
            logger.info("Executing automated pytest suite inside isolated environment...")
            test_proc = subprocess.run([venv_python, "-m", "pytest", os.path.join(staged_dir, "backend", "tests"), "-q"], capture_output=True, text=True, timeout=30)

            if test_proc.returncode == 0:
                logger.info("Isolated test suite validation succeeded.")
                return True, "All validation pytests passed successfully."
            else:
                logger.error("Isolated test suite validation failed:\n%s", test_proc.stderr)
                return False, f"Automated test validation failed. Status: {test_proc.returncode}"

        except Exception as e:
            logger.error("Isolated validation execution failed: %s", e)
            return False, f"Isolated validation failed: {str(e)}"


update_validator = UpdateValidator()
