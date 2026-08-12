# core/update/version_manager.py
import os
import json
import logging

logger = logging.getLogger("ultron-api")
ACTIVE_RELEASE_FILE = "active_release.json"


class VersionManager:
    """Manages immutable release identities, current active versions, and registry mappings."""

    def __init__(self):
        self.default_identity = {
            "application_version": "1.0.0",
            "release_id": "rel_initial_v100",
            "manifest_hash": "b8a3e91f04ca31d",
            "artifact_sha256": "3a8a447fca4cfb264",
            "source_commit": "3569a12793d75fb3",
            "creation_timestamp": "2026-08-11T12:00:00Z"
        }
        self.active_identity = self.load_active_release()

    def load_active_release(self) -> dict:
        """Loads the active release metadata safely from local storage."""
        if os.path.exists(ACTIVE_RELEASE_FILE):
            try:
                with open(ACTIVE_RELEASE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                merged = dict(self.default_identity)
                merged.update(data)
                return merged
            except Exception as e:
                logger.error("Failed to load active release metadata: %s", e)
        return dict(self.default_identity)

    def save_active_release(self, release_identity: dict) -> bool:
        """Persists the newly activated immutable release identity locally."""
        try:
            with open(ACTIVE_RELEASE_FILE, "w", encoding="utf-8") as f:
                json.dump(release_identity, f, indent=4)
            self.active_identity = release_identity
            logger.info("Activated new release identity: %s", release_identity["release_id"])
            return True
        except Exception as e:
            logger.error("Failed to save active release identity: %s", e)
            return False


version_manager = VersionManager()
