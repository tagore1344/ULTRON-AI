# core/context/long_term_goals.py
import os
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")


class LongTermGoalManager:
    """Manages persistent cross-session long-term goals, subgoal dependencies, and reboot re-hydration."""

    def __init__(self):
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Returns thread-safe connection to the context database."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Initializes the database schema for goal ledgers."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Long Term Goals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term_goals (
                goal_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                status TEXT NOT NULL CHECK (status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'BLOCKED', 'COMPLETED', 'FAILED', 'CANCELLED')),
                success_criteria TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deadline TEXT,
                last_progress_update TEXT NOT NULL,
                next_planned_action TEXT
            )
        """)

        # 2. Subgoals & Checkpoints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subgoals (
                subgoal_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL REFERENCES long_term_goals(goal_id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')),
                dependencies TEXT, -- Comma-separated subgoal_ids
                checkpoint_state TEXT, -- Serialized JSON state checkpoint
                retry_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def create_goal(
        self,
        goal_id: str,
        description: str,
        priority: str = "MEDIUM",
        success_criteria: str = "Completed successfully",
        deadline: Optional[str] = None
    ) -> bool:
        """Registers a new persistent long-term goal."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO long_term_goals (
                    goal_id, description, priority, status, success_criteria, created_at, deadline, last_progress_update
                ) VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
                """,
                (goal_id, description, priority, success_criteria, timestamp, deadline, timestamp)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to persist long-term goal: %s", e)
            return False
        finally:
            conn.close()

    def create_subgoal(
        self,
        subgoal_id: str,
        goal_id: str,
        description: str,
        dependencies: Optional[str] = None,
        checkpoint_state: Optional[str] = None
    ) -> bool:
        """Registers a dependent subgoal checkpoint."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO subgoals (
                    subgoal_id, goal_id, description, status, dependencies, checkpoint_state, retry_count
                ) VALUES (?, ?, ?, 'PENDING', ?, ?, 0)
                """,
                (subgoal_id, goal_id, description, dependencies, checkpoint_state)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to persist subgoal: %s", e)
            return False
        finally:
            conn.close()

    def update_goal_status(self, goal_id: str, status: str):
        """Updates the status of a long-term goal."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE long_term_goals SET status = ?, last_progress_update = ? WHERE goal_id = ?",
            (status, timestamp, goal_id)
        )
        conn.commit()
        conn.close()

    def update_subgoal_status(self, subgoal_id: str, status: str, checkpoint: Optional[str] = None):
        """Updates the status of a subgoal checkpoint."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if checkpoint:
            cursor.execute(
                "UPDATE subgoals SET status = ?, checkpoint_state = ? WHERE subgoal_id = ?",
                (status, checkpoint, subgoal_id)
            )
        else:
            cursor.execute(
                "UPDATE subgoals SET status = ? WHERE subgoal_id = ?",
                (status, subgoal_id)
            )
        conn.commit()
        conn.close()

    def get_active_goals_with_subgoals(self) -> List[Dict[str, Any]]:
        """Retrieves active goals along with their nested subgoals."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM long_term_goals WHERE status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'BLOCKED')")
        goals = [dict(row) for row in cursor.fetchall()]

        for goal in goals:
            cursor.execute("SELECT * FROM subgoals WHERE goal_id = ?", (goal["goal_id"],))
            goal["subgoals"] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return goals

    # ==============================================================================
    # STARTUP REBOOT RE-HYDRATION
    # ==============================================================================

    def rehydrate_goals_on_boot(self) -> List[Dict[str, Any]]:
        """
        Scans all unfinished persistent goals during system boot.
        Safely re-hydrates subgoals.
        DANGEROUS or high-risk tasks are statefully set to 'SUSPENDED' to prevent auto-runs.
        """
        logger.info("Initializing cross-session long-term goal boot re-hydration...")
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Fetch active goals from prior session
        cursor.execute("SELECT * FROM long_term_goals WHERE status IN ('ACTIVE', 'PENDING')")
        active_goals = [dict(row) for row in cursor.fetchall()]

        rehydrated = []
        for goal in active_goals:
            goal_id = goal["goal_id"]

            # Fetch subgoals
            cursor.execute("SELECT * FROM subgoals WHERE goal_id = ?", (goal_id,))
            subgoals = [dict(row) for row in cursor.fetchall()]

            # Safety Validation check: Identify dangerous intents
            is_dangerous = False
            for sg in subgoals:
                desc = sg["description"].lower()
                # Blacklisted keywords triggering safe suspension on startup
                if any(k in desc for w in ("whatsapp", "volume", "open", "message", "shutdown", "restart") for k in w.split()):
                    is_dangerous = True
                    break

            if is_dangerous:
                # Security Immutability Safeguard: Force SUSPENDED on high-risk restarts
                logger.warning("Goal '%s' contains potentially dangerous or external tools. Suspending to prevent raw auto-resume loops.", goal_id)
                cursor.execute("UPDATE long_term_goals SET status = 'SUSPENDED' WHERE goal_id = ?", (goal_id,))
                goal["status"] = "SUSPENDED"
            else:
                logger.info("Goal '%s' successfully re-hydrated to ACTIVE state.", goal_id)
                cursor.execute("UPDATE long_term_goals SET status = 'ACTIVE' WHERE goal_id = ?", (goal_id,))
                goal["status"] = "ACTIVE"

            goal["subgoals"] = subgoals
            rehydrated.append(goal)

        conn.commit()
        conn.close()
        return rehydrated


# Singleton Goal Manager instance
goal_manager_9b = LongTermGoalManager()
