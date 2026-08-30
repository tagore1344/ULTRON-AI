# core/update/staged_release.py
import os
import subprocess
import shutil
import zipfile
import logging
from typing import Tuple, List

logger = logging.getLogger("ultron-api")
RELEASES_DIR = "releases"


class StagedRelease:
    """Manages the isolated, versioned staged releases directory tree, and enforces Git worktree safety blocks."""

    def __init__(self):
        os.makedirs(RELEASES_DIR, exist_ok=True)

    def check_worktree_safety(self) -> Tuple[bool, List[str]]:
        """
        Enforce absolute local Git worktree safety.
        Returns False and the list of uncommitted/untracked files if any modifications exist.
        """
        try:
            # Check for modified tracked files
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False
            )
            if status_proc.returncode == 0:
                lines = [line.strip() for line in status_proc.stdout.split("\n") if line.strip()]
                if lines:
                    logger.warning("Worktree safety block triggered. Uncommitted local modifications found.")
                    return False, lines
            return True, []
        except Exception as e:
            logger.error("Git worktree safety check failed to execute: %s", e)
            return False, ["Git command execution error."]

    def stage_release(self, version: str, zip_filepath: str) -> str:
        """Unpacks the verified release zip into an isolated, versioned release subdirectory, with strict Zip-Slip guards."""
        target_dir = os.path.join(RELEASES_DIR, f"release_v{version.replace('.', '_')}")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        logger.info("Staging release %s into isolated directory with Zip-Slip guards: %s", version, target_dir)

        try:
            # Enforce Zip-Slip Traversal Guards during extraction
            with zipfile.ZipFile(zip_filepath, 'r') as archive:
                for member in archive.namelist():
                    # Reject members attempting directory traversal, absolute paths, or drive roots
                    normalized_member = os.path.normpath(member)
                    if (normalized_member.startswith("..") or
                            os.path.isabs(normalized_member) or
                            ":" in normalized_member or
                            "\\\\" in normalized_member):
                        logger.error("Security alert: Blocked malicious zip member attempting traversal: '%s'", member)
                        raise PermissionError(f"Malicious directory traversal attempt blocked: '{member}'")

                # If all members are safe, proceed to extract
                archive.extractall(target_dir)
            return target_dir
        except Exception as e:
            logger.error("Failed to safely unpack staged release package: %s", e)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            raise RuntimeError(f"Unpacking staged release failed: {e}")


staged_release = StagedRelease()
