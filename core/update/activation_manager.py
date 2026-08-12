# core/update/activation_manager.py
import datetime
import logging
from core.update.version_manager import version_manager

logger = logging.getLogger("ultron-api")


class ActivationManager:
    """Handles atomic, cross-platform release switching by updating localized immutable active release pointers."""

    def activate_release(self, version: str, release_id: str, manifest_hash: str, artifact_sha256: str, source_commit: str) -> bool:
        """Atomically switches the active release by writing the new immutable release identity to active_release.json."""
        logger.info("Initiating atomic activation switch for release %s...", release_id)

        new_identity = {
            "application_version": version,
            "release_id": release_id,
            "manifest_hash": manifest_hash,
            "artifact_sha256": artifact_sha256,
            "source_commit": source_commit,
            "creation_timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

        # Save and swap the active release pointer atomically
        success = version_manager.save_active_release(new_identity)
        if success:
            logger.info("Release %s activated successfully on this host.", release_id)
            return True
        else:
            logger.error("Failed to activate release %s.", release_id)
            return False


activation_manager = ActivationManager()
