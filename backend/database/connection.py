# backend/database/connection.py
import os
import sqlite3
import logging

logger = logging.getLogger("ultron-api")
DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_devices.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns a parameterized thread-safe SQLite connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Enable dict-like row access factory
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """Performs stateful, automated directory creation and schema deployments on server boot."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
        logger.info("Created local database storage directory: %s", DB_DIR)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create devices registration table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            device_name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            permissions TEXT NOT NULL,
            created_at TEXT NOT NULL,
            paired_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            revoked INTEGER DEFAULT 0
        )
    """)

    # 2. Create pairing sessions tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pairing_sessions (
            session_id TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )
    """)

    # 3. Create rate limiting tracker table to prevent brute forcing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brute_force_tracker (
            ip_address TEXT PRIMARY KEY,
            failed_attempts INTEGER DEFAULT 0,
            last_attempt_at TEXT NOT NULL,
            locked_until TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("SQLite device database successfully initialized at: %s", DB_PATH)
