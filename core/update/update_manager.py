# core/update/update_manager.py
import datetime
import logging
from typing import Dict, Any, Tuple

from core.update.version_manager import version_manager
from core.update.update_checker import update_checker
from core.update.update_planner import update_planner
from core.update.update_policy import update_policy, UpdateRiskClass
from core.update.update_downloader import update_downloader
from core.update.staged_release import staged_release
from core.update.update_validator import update_validator
from core.update.activation_manager import activation_manager
from core.update.rollback_manager import rollback_manager
from backend.security.token_service import token_service

logger = logging.getLogger("ultron-api")


class UpdateManager:
    """Master coordinator of the autonomous self-update subsystem."""

    def __init__(self):
        self.state = "IDLE"  # CHECKING, UPDATE_AVAILABLE, DOWNLOADING, VERIFYING, STAGING, VALIDATING, ACTIVATING, HEALTH_CHECK, SUCCESS, ROLLBACK, FAILED, BLOCKED
        self.history = []
        self.retry_counter = {}

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "current_release": version_manager.active_identity,
            "update_history_count": len(self.history)
        }

    async def check_and_apply_update(self, manifest_bytes: bytes, signature: bytes, package_filepath: str) -> Tuple[bool, str]:
        """Orchestrates the complete secure autonomous self-update transaction lifecycle."""
        self.state = "CHECKING"

        # 1. Verify working tree status (Worktree Safety Rule)
        safe, modified_files = staged_release.check_worktree_safety()
        if not safe:
            self.state = "BLOCKED"
            logger.error("Update blocked: uncommitted changes present in local repository.")
            return False, f"Update blocked. Stale local files: {', '.join(modified_files[:3])}"

        # 2. Cryptographic Manifest Signature Verification
        verified_sig = update_checker.verify_manifest_signature(manifest_bytes, signature)
        if not verified_sig:
            self.state = "FAILED"
            return False, "Cryptographic signature verification failed. Manifest untrusted."

        # Parse manifest content
        try:
            import json
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except Exception as e:
            self.state = "FAILED"
            return False, f"Malformed manifest JSON: {e}"

        # Verify repository/branch bounds
        if not update_checker.validate_manifest_meta(manifest):
            self.state = "FAILED"
            return False, "Repository/Branch authenticity verification failed."

        # 3. Update discovery/planning
        self.state = "UPDATE_AVAILABLE"
        allowed, reason = update_planner.evaluate_manifest(manifest)
        if not allowed:
            self.state = "BLOCKED"
            return False, reason

        # 4. Download and Verify Checksums
        self.state = "DOWNLOADING"
        expected_sha = manifest.get("checksum", "")
        self.state = "VERIFYING"
        if not update_downloader.verify_checksum(package_filepath, expected_sha):
            self.state = "FAILED"
            return False, "SHA-256 Checksum mismatch. Download corrupted."

        # 5. Classify risk levels
        modified_list = manifest.get("modified_files", [])
        risk_class = update_policy.classify_update(modified_list)
        logger.info("Update classified under risk category: %s", risk_class.value)

        # 6. Stage Release into isolated directory
        self.state = "STAGING"
        target_version = manifest.get("version", "0.0.0")
        try:
            staged_dir = staged_release.stage_release(target_version, package_filepath)
        except Exception as e:
            self.state = "FAILED"
            return False, str(e)

        # Record pre-update identity for rollback references
        previous_identity = dict(version_manager.active_identity)

        # 7. Isolated Validation Environment
        self.state = "VALIDATING"
        test_passed, test_reason = update_validator.run_isolated_validation(staged_dir)
        if not test_passed:
            # Add commit hash to blacklist to prevent infinite upgrade loops
            update_planner.blacklist_commit(manifest.get("commit", ""))

            self.state = "ROLLBACK"
            logger.warning("Staged release failed validation pytests. Restoring pristine previous release.")
            return False, f"Staged release failed validation. Reason: {test_reason}"

        # 8. Activating Target Release
        self.state = "ACTIVATING"
        release_id = f"rel_{target_version.replace('.', '_')}_{uuid_4_hex()}"
        success = activation_manager.activate_release(
            version=target_version,
            release_id=release_id,
            manifest_hash=token_service.hash_string(manifest_bytes.decode("utf-8")),
            artifact_sha256=expected_sha,
            source_commit=manifest.get("commit", "")
        )

        if not success:
            self.state = "ROLLBACK"
            rollback_manager.revert_release_pointer(previous_identity)
            return False, "Activation pointer swap failed."

        # 9. Health Monitoring (Simulated in Stage 1-2, returns success after all validation)
        self.state = "HEALTH_CHECK"
        self.state = "SUCCESS"

        # Record persistent history
        self._record_history(previous_identity, manifest, risk_class, "SUCCESS", "")
        return True, "Autonomous update completed successfully."

    def _record_history(self, old: dict, manifest: dict, risk: UpdateRiskClass, status: str, rollback_reason: str):
        self.history.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "old_version": old["application_version"],
            "new_version": manifest.get("version", "0.0.0"),
            "commit": manifest.get("commit", ""),
            "manifest_version": manifest.get("manifest_version", "1.0.0"),
            "risk_class": risk.value,
            "validation_result": status,
            "rollback_reason": rollback_reason
        })


def uuid_4_hex():
    import uuid
    return uuid.uuid4().hex[:12]


update_manager = UpdateManager()
