# core/update/update_downloader.py
import os
import hashlib
import logging

logger = logging.getLogger("ultron-api")


class UpdateDownloader:
    """Handles downloading and validating cryptographic SHA-256 checksums of update packages."""

    def __init__(self):
        self.download_dir = "backend/data/updates/tmp"
        os.makedirs(self.download_dir, exist_ok=True)

    def verify_checksum(self, filepath: str, expected_sha256: str) -> bool:
        """Verifies that the downloaded artifact file's SHA-256 checksum matches the manifest exactly."""
        if not os.path.exists(filepath):
            logger.error("Download verification failed: Target file %s does not exist.", filepath)
            return False

        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                # Read in secure 4K chunks to handle large files cleanly
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            calculated_sha = sha256_hash.hexdigest()
            if calculated_sha == expected_sha256:
                logger.info("SHA-256 checksum matched successfully: %s", expected_sha256)
                return True
            else:
                logger.error("SHA-256 checksum mismatch! Expected: %s, got: %s", expected_sha256, calculated_sha)
                return False
        except Exception as e:
            logger.error("Error calculating file checksum: %s", e)
            return False


update_downloader = UpdateDownloader()
