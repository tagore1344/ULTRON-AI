# core/update/update_planner.py
from typing import Tuple
import logging
from core.update.version_manager import version_manager

logger = logging.getLogger("ultron-api")


class UpdatePlanner:
    """Manages update scheduling, blocks downgrades, and checks for commit blacklists."""

    def __init__(self):
        # Maps failed commit blacklists in memory or DB to prevent loops
        # In a fully deployed SQLite registry, we will maintain a dedicated 'failed_updates' table
        self.blacklisted_commits = set()

    def evaluate_manifest(self, manifest: dict) -> Tuple[bool, str]:
        """Assess the update manifest for version compatibility, downgrade blocks, and blacklist loops."""
        target_version = manifest.get("version", "0.0.0")
        target_commit = manifest.get("commit", "")

        current_version = version_manager.active_identity["application_version"]

        # 1. Downgrade Blocking
        if self._is_downgrade(target_version, current_version):
            logger.warning("Update rejected: Attempted downgrade from %s to %s.", current_version, target_version)
            return False, "Downgrade prevention triggered. Cannot install an older build version."

        # 2. Blacklist Loop Checking
        if target_commit in self.blacklisted_commits:
            logger.warning("Update rejected: Target commit %s is currently blacklisted due to previous failures.", target_commit)
            return False, "Failed commit loop prevention triggered. Target release has previous validation failures."

        return True, "Ready"

    def blacklist_commit(self, commit_hash: str):
        """Statefully blacklist a failed commit hash from being auto-updated again."""
        if commit_hash:
            self.blacklisted_commits.add(commit_hash)
            logger.warning("Commit hash %s has been blacklisted due to validation failures.", commit_hash)

    def _is_downgrade(self, target: str, current: str) -> bool:
        """Compares two semantic versions and returns True if target is older than current."""
        try:
            t_parts = [int(x) for x in target.split(".")]
            c_parts = [int(x) for x in current.split(".")]
            for tp, cp in zip(t_parts, c_parts):
                if tp < cp:
                    return True
                elif tp > cp:
                    return False
        except:
            pass
        return False


update_planner = UpdatePlanner()
