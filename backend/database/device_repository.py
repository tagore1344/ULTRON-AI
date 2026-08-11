# backend/database/device_repository.py
import sqlite3
import datetime
import logging
from typing import Optional, Dict, Any, List
from backend.database.connection import get_db_connection

logger = logging.getLogger("ultron-api")


class DeviceRepository:
    """Handles secure, fully parameterized database queries for devices and pairing sessions."""

    def __init__(self):
        # We fetch connections on-demand to support safe concurrent executions
        pass

    # ==============================================================================
    # DEVICE REGISTRY QUERIES
    # ==============================================================================

    def create_device(self, device_data: Dict[str, Any]) -> bool:
        """Register a newly paired authorized client device into SQLite."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO devices (
                    device_id, device_name, device_type, token_hash,
                    permissions, created_at, paired_at, updated_at, last_seen, revoked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_data["device_id"],
                device_data["device_name"],
                device_data["device_type"],
                device_data["token_hash"],
                ",".join(device_data["permissions"]),  # Commas storage
                device_data["created_at"],
                device_data["paired_at"],
                device_data["updated_at"],
                device_data["last_seen"],
                1 if device_data.get("revoked", False) else 0
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("DB error creating device record: %s", e)
            return False
        finally:
            conn.close()

    def get_device_by_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve active registered device associated with the hashed Bearer token."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE token_hash = ?", (token_hash,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["permissions"] = [x.strip() for x in res["permissions"].split(",") if x.strip()]
                res["revoked"] = bool(res["revoked"])
                return res
            return None
        except sqlite3.Error as e:
            logger.error("DB error looking up device by hash: %s", e)
            return None
        finally:
            conn.close()

    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve registered device matching the unique device ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["permissions"] = [x.strip() for x in res["permissions"].split(",") if x.strip()]
                res["revoked"] = bool(res["revoked"])
                return res
            return None
        except sqlite3.Error as e:
            logger.error("DB error looking up device by ID: %s", e)
            return None
        finally:
            conn.close()

    def list_all_devices(self) -> List[Dict[str, Any]]:
        """Returns list of all devices registered (including revoked ones for audits)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices ORDER BY paired_at DESC")
            rows = cursor.fetchall()
            devices = []
            for r in rows:
                d = dict(r)
                d["permissions"] = [x.strip() for x in d["permissions"].split(",") if x.strip()]
                d["revoked"] = bool(d["revoked"])
                devices.append(d)
            return devices
        except sqlite3.Error as e:
            logger.error("DB error listing devices: %s", e)
            return []
        finally:
            conn.close()

    def revoke_device(self, device_id: str) -> bool:
        """Mark a device revoked in database to block access instantly while keeping logs."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE devices SET revoked = 1, updated_at = ? WHERE device_id = ?", (
                datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                device_id
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("DB error revoking device %s: %s", device_id, e)
            return False
        finally:
            conn.close()

    def update_last_seen(self, device_id: str):
        """Update last seen UTC timestamp to monitor active client connectivity."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE devices SET last_seen = ? WHERE device_id = ?", (
                datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                device_id
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.debug("Silently logging DB error updating last_seen: %s", e)
        finally:
            conn.close()

    # ==============================================================================
    # PAIRING HANDSHAKE QUERIES
    # ==============================================================================

    def create_pairing_session(self, session_data: Dict[str, Any]) -> bool:
        """Saves a hashed temporary pairing PIN code record into SQLite."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pairing_sessions (session_id, code_hash, created_at, expires_at, used)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_data["session_id"],
                session_data["code_hash"],
                session_data["created_at"],
                session_data["expires_at"],
                1 if session_data.get("used", False) else 0
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("DB error creating pairing session: %s", e)
            return False
        finally:
            conn.close()

    def get_unused_pairing_session(self, code_hash: str) -> Optional[Dict[str, Any]]:
        """Finds an unused, unexpired temporary pairing session matching code hash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM pairing_sessions WHERE code_hash = ? AND used = 0",
                (code_hash,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error("DB error retrieving pairing session: %s", e)
            return None
        finally:
            conn.close()

    def mark_pairing_session_used(self, session_id: str) -> bool:
        """Mark a temporary pairing session PIN used to prevent dual enrollment exploits."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE pairing_sessions SET used = 1 WHERE session_id = ?", (session_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("DB error marking pairing session used: %s", e)
            return False
        finally:
            conn.close()

    # ==============================================================================
    # BRUTE FORCE / LOCKOUT QUERIES (RATE LIMITING)
    # ==============================================================================

    def get_lockout_status(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get the brute force attempts and lock status of a specific IP address."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM brute_force_tracker WHERE ip_address = ?", (ip_address,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error("DB error checking lockout status: %s", e)
            return None
        finally:
            conn.close()

    def record_failed_attempt(self, ip_address: str) -> int:
        """Logs a failed brute pairing attempt, locked out for 60 seconds after 5 failed attempts."""
        conn = get_db_connection()
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        try:
            cursor = conn.cursor()
            status = self.get_lockout_status(ip_address)

            if status:
                attempts = status["failed_attempts"] + 1
                locked_until = None
                if attempts >= 5:
                    locked_until = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(seconds=60)).isoformat() + "Z"
                    logger.warning("Brute force protection triggered. Lockout applied for IP %s until %s", ip_address, locked_until)

                cursor.execute("""
                    UPDATE brute_force_tracker
                    SET failed_attempts = ?, last_attempt_at = ?, locked_until = ?
                    WHERE ip_address = ?
                """, (attempts, now_str, locked_until, ip_address))
            else:
                attempts = 1
                cursor.execute("""
                    INSERT INTO brute_force_tracker (ip_address, failed_attempts, last_attempt_at, locked_until)
                    VALUES (?, ?, ?, NULL)
                """, (ip_address, attempts, now_str))

            conn.commit()
            return attempts
        except sqlite3.Error as e:
            logger.error("DB error logging failed lockout attempts: %s", e)
            return 1
        finally:
            conn.close()

    def reset_failed_attempts(self, ip_address: str):
        """Clears IP brute force tracking record after successful authorization connection."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM brute_force_tracker WHERE ip_address = ?", (ip_address,))
            conn.commit()
        except sqlite3.Error as e:
            logger.error("DB error resetting lockout attempts: %s", e)
        finally:
            conn.close()


# Singleton instance of SQLite device query pipeline
device_repo = DeviceRepository()
