# core/update/rollback_manager.py
import sqlite3
import logging
from backend.database.connection import get_db_connection
from core.update.version_manager import version_manager

logger = logging.getLogger("ultron-api")


class RollbackManager:
    """Manages transactional SQLite migration rollbacks, and reverts active release pointers on failure."""

    def rollback_database_migration(self, rollback_script_path: str) -> bool:
        """Runs the inverse versioned rollback SQL script inside a transactional SQLite block."""
        logger.warning("Initiating transactional database migration rollback...")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # 1. Start transactional SQL block
            cursor.execute("BEGIN TRANSACTION")

            with open(rollback_script_path, "r", encoding="utf-8") as f:
                sql_script = f.read()

            # Execute the rollback script statefully
            cursor.executescript(sql_script)

            # 2. Commit transaction on success
            conn.commit()
            logger.info("Database migration rolled back successfully inside SQL transaction.")
            return True
        except Exception as e:
            logger.error("Transactional database migration rollback failed: %s", e)
            try:
                # Rollback transaction on failure
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def revert_release_pointer(self, previous_release_identity: dict) -> bool:
        """Reverts the active release JSON pointer back to the last known-good state."""
        logger.warning("Reverting active release pointer back to: %s", previous_release_identity.get("release_id"))
        return version_manager.save_active_release(previous_release_identity)


rollback_manager = RollbackManager()
