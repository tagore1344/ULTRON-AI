# backend/tests/test_update.py
import pytest
import os
import json
import shutil
import zipfile
import asyncio
from unittest.mock import MagicMock, patch

from core.update.update_manager import update_manager, uuid_4_hex
from core.update.version_manager import version_manager
from core.update.update_checker import update_checker
from core.update.update_planner import update_planner
from core.update.update_policy import update_policy, UpdateRiskClass
from core.update.update_downloader import update_downloader
from core.update.staged_release import staged_release
from core.update.update_validator import update_validator
from core.update.activation_manager import activation_manager
from core.update.rollback_manager import rollback_manager


@pytest.fixture(autouse=True)
def clean_update_states():
    """Ensure update manager, blacklists, and directories are fresh and isolated for each test."""
    update_manager.state = "IDLE"
    update_planner.blacklisted_commits.clear()
    os.environ["ULTRON_TEST_MODE"] = "true"

    # Reset active_release configuration
    version_manager.save_active_release(version_manager.default_identity)

    tmp_releases = "releases"
    if os.path.exists(tmp_releases):
        try:
            shutil.rmtree(tmp_releases)
        except:
            pass
    os.makedirs(tmp_releases, exist_ok=True)
    yield
    os.environ.pop("ULTRON_TEST_MODE", None)


@pytest.mark.anyio
async def test_update_lifecycle_success():
    """Verify that a standard, trusted release candidate update passes all checks and activates statefully."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "version": "1.1.0",
        "commit": "835cf09a06ff5e43",
        "repository": "tagore1344/ULTRON-AI",
        "branch": "arena/019fef42-ultron-ai",
        "checksum": "mock_checksum_sha256_123",
        "modified_files": ["ai/agents/gemini_agent.py"]
    }
    manifest_bytes = json.dumps(manifest_data).encode("utf-8")

    # Mock zip file creation
    zip_path = "releases/test_success.zip"
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr("test_file.txt", "content")

    # 1. Mock secure signature checks and worktree safety
    with patch.object(update_checker, "verify_manifest_signature", return_value=True), \
         patch.object(staged_release, "check_worktree_safety", return_value=(True, [])) as mock_safety, \
         patch.object(update_downloader, "verify_checksum", return_value=True):

        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath=zip_path
        )

        assert success is True
        assert update_manager.state == "SUCCESS"
        assert version_manager.active_identity["application_version"] == "1.1.0"
        assert version_manager.active_identity["source_commit"] == "835cf09a06ff5e43"


@pytest.mark.anyio
async def test_update_blocked_on_dirty_worktree():
    """Verify that uncommitted modifications in your Git tree block auto-updates completely."""
    manifest_bytes = b"{}"

    # Simulate dirty worktree containing uncommitted files
    with patch.object(staged_release, "check_worktree_safety", return_value=(False, ["app_controller.py"])):
        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath="test_pack.zip"
        )
        assert success is False
        assert update_manager.state == "BLOCKED"
        assert "blocked" in msg.lower()


@pytest.mark.anyio
async def test_update_signature_mismatch_rejected():
    """Verify that unsigned or malicious signature manifests are rejected instantly by the public key scanner."""
    manifest_bytes = b'{"version": "1.1.0"}'

    with patch.object(staged_release, "check_worktree_safety", return_value=(True, [])):
        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"fake_untrusted_signature",
            package_filepath="test_pack.zip"
        )
        assert success is False
        assert update_manager.state == "FAILED"
        assert "signature" in msg.lower()


@pytest.mark.anyio
async def test_update_downgrade_blocked():
    """Verify that downgrade prevention stops clients from installing older build versions."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "version": "0.9.0", # Downgrade (current is 1.0.0)
        "commit": "old_commit_hash",
        "repository": "tagore1344/ULTRON-AI",
        "branch": "arena/019fef42-ultron-ai",
        "checksum": "mock_checksum_sha256_123"
    }
    manifest_bytes = json.dumps(manifest_data).encode("utf-8")

    with patch.object(update_checker, "verify_manifest_signature", return_value=True), \
         patch.object(staged_release, "check_worktree_safety", return_value=(True, [])):

        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath="test_pack.zip"
        )
        assert success is False
        assert update_manager.state == "BLOCKED"
        assert "downgrade" in msg.lower()


@pytest.mark.anyio
async def test_update_loop_prevention_blacklist():
    """Verify that a failed commit is blacklisted, blocking infinite update loops."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "version": "1.1.0",
        "commit": "failed_commit_hash",
        "repository": "tagore1344/ULTRON-AI",
        "branch": "arena/019fef42-ultron-ai",
        "checksum": "mock_checksum_sha256_123"
    }
    manifest_bytes = json.dumps(manifest_data).encode("utf-8")

    # Blacklist this commit
    update_planner.blacklist_commit("failed_commit_hash")

    with patch.object(update_checker, "verify_manifest_signature", return_value=True), \
         patch.object(staged_release, "check_worktree_safety", return_value=(True, [])):

        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath="test_pack.zip"
        )
        assert success is False
        assert "loop prevention" in msg.lower() or "blacklist" in msg.lower()


@pytest.mark.anyio
async def test_update_checksum_mismatch_rejected():
    """Verify that downloaded packages with mismatched SHA-256 hash checksums are blocked."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "version": "1.1.0",
        "commit": "835cf09a06ff5e43",
        "repository": "tagore1344/ULTRON-AI",
        "branch": "arena/019fef42-ultron-ai",
        "checksum": "expected_sha_abc123"
    }
    manifest_bytes = json.dumps(manifest_data).encode("utf-8")

    with patch.object(update_checker, "verify_manifest_signature", return_value=True), \
         patch.object(staged_release, "check_worktree_safety", return_value=(True, [])):

        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath="test_pack.zip"
        )
        assert success is False
        assert update_manager.state == "FAILED"
        assert "checksum" in msg.lower()


@pytest.mark.anyio
async def test_update_blocked_on_zip_slip_traversal():
    """Verify that malicious zip archives attempting Zip-Slip directory traversals are strictly blocked."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "version": "1.1.0",
        "commit": "835cf09a06ff5e43",
        "repository": "tagore1344/ULTRON-AI",
        "branch": "arena/019fef42-ultron-ai",
        "checksum": "expected_sha_123"
    }
    manifest_bytes = json.dumps(manifest_data).encode("utf-8")

    # Create a malicious zip payload containing a relative path traversal member
    zip_path = "releases/malicious_slip.zip"
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr("../../malicious_slip.txt", "malicious_payload")

    with patch.object(update_checker, "verify_manifest_signature", return_value=True), \
         patch.object(staged_release, "check_worktree_safety", return_value=(True, [])), \
         patch.object(update_downloader, "verify_checksum", return_value=True):

        success, msg = await update_manager.check_and_apply_update(
            manifest_bytes=manifest_bytes,
            signature=b"mock_staged_sig_123",
            package_filepath=zip_path
        )
        assert success is False
        assert update_manager.state == "FAILED"
        assert "traversal" in msg.lower()


def test_update_risk_classification():
    """Verify that modified files map correctly to their corresponding risk categories."""
    assert update_policy.classify_update(["docs/SECURITY.md"]) == UpdateRiskClass.SAFE_AUTOMATIC
    assert update_policy.classify_update(["app_controller.py"]) == UpdateRiskClass.REVIEW_REQUIRED
    assert update_policy.classify_update(["backend/security/authentication.py"]) == UpdateRiskClass.HIGH_RISK
