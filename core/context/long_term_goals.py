# core/context/long_term_goals.py
import os
import json
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")


class LongTermGoalManager:
    """Manages persistent cross-session long-term goals, subgoal dependencies, priority scheduling, and re-hydration."""

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
                dependencies TEXT, -- Comma-separated sibling subgoal_ids
                checkpoint_state TEXT, -- Serialized JSON state checkpoint
                retry_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()

        # Schema Migrations: Add active_hypothesis_id, active_experiment_id, and last_successful_action columns if missing
        try:
            cursor.execute("ALTER TABLE long_term_goals ADD COLUMN active_hypothesis_id TEXT")
            cursor.execute("ALTER TABLE long_term_goals ADD COLUMN active_experiment_id TEXT")
            cursor.execute("ALTER TABLE long_term_goals ADD COLUMN last_successful_action TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Already exists from prior schema migrations

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
        timestamp = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO long_term_goals (
                    goal_id, description, priority, status, success_criteria, created_at, deadline, last_progress_update,
                    active_hypothesis_id, active_experiment_id, last_successful_action
                ) VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?, NULL, NULL, NULL)
                """,
                (goal_id, description, priority, success_criteria, timestamp, deadline, timestamp)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to persist long-term goal: %s", e)
            try:
                conn.rollback()
            except:
                pass
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
                ON CONFLICT(subgoal_id) DO UPDATE SET
                    description = EXCLUDED.description,
                    dependencies = EXCLUDED.dependencies,
                    checkpoint_state = EXCLUDED.checkpoint_state
                """,
                (subgoal_id, goal_id, description, dependencies, checkpoint_state)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to persist subgoal: %s", e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def update_goal_status(self, goal_id: str, status: str):
        """Updates the status of a long-term goal."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
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

    def update_goal_hypotheses_and_experiments(
        self,
        goal_id: str,
        hypothesis_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        last_action: Optional[str] = None
    ):
        """Updates persistent learning tracking variables for a long-term goal."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE long_term_goals
            SET active_hypothesis_id = ?, active_experiment_id = ?, last_successful_action = ?
            WHERE goal_id = ?
            """,
            (hypothesis_id, experiment_id, last_action, goal_id)
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
    # PRIORITIZATION & PROGRESS EVALUATION
    # ==============================================================================

    def calculate_priority_score(self, goal: Dict[str, Any]) -> float:
        """
        Calculates a priority score (0.0 to 200.0) based on urgency, deadline proximity, and status.
        Blocked goals are forced to 0.0 to prevent duplicate execution runs.
        """
        if goal["status"] == "BLOCKED":
            return 0.0

        # Base weights
        weights = {"CRITICAL": 100.0, "HIGH": 75.0, "MEDIUM": 50.0, "LOW": 25.0}
        score = weights.get(goal["priority"], 50.0)

        # Urgency / Deadline factor
        deadline_str = goal.get("deadline")
        if deadline_str:
            try:
                deadline_dt = datetime.datetime.fromisoformat(deadline_str.replace("Z", ""))
                time_left = (deadline_dt - datetime.datetime.now()).total_seconds() / 3600.0
                # Closer deadlines scale urgency score up to +100.0 bonus
                urgency = 100.0 / (max(0.1, time_left) + 1.1)
                score += urgency
            except Exception:
                pass

        return round(score, 2)

    def evaluate_goal_progress(self, goal_id: str) -> Dict[str, Any]:
        """
        Calculates completion percentage, estimated remaining work,
        blockers, success probability, and resource usage for a long-term goal.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subgoals WHERE goal_id = ?", (goal_id,))
        subgoals = [dict(row) for row in cursor.fetchall()]
        conn.close()

        total = len(subgoals)
        if total == 0:
            return {
                "progress_percentage": 0.0,
                "completed_count": 0,
                "total_count": 0,
                "remaining_count": 0,
                "blockers": [],
                "success_probability": 0.95
            }

        completed = sum(1 for sg in subgoals if sg["status"] == "SUCCESS")
        failed = sum(1 for sg in subgoals if sg["status"] == "FAILED")
        remaining = total - completed - failed

        # Check for dependency blockers
        blockers = []
        for sg in subgoals:
            if sg["status"] == "PENDING" and sg.get("dependencies"):
                deps = [d.strip() for d in sg["dependencies"].split(",") if d.strip()]
                for dep in deps:
                    # Find dependency state
                    dep_sg = next((s for s in subgoals if s["subgoal_id"] == dep), None)
                    if dep_sg and dep_sg["status"] != "SUCCESS":
                        blockers.append(f"Subgoal {sg['subgoal_id']} is blocked by incomplete dependency {dep}")

        # Subjective success probability decreases as subgoals fail or retries accumulate
        success_prob = max(0.1, 0.95 - (failed * 0.15))

        return {
            "progress_percentage": round((completed / total) * 100.0, 1),
            "completed_count": completed,
            "total_count": total,
            "remaining_count": remaining,
            "blockers": blockers,
            "success_probability": round(success_prob, 2)
        }

    def get_ranked_goals(self) -> List[Dict[str, Any]]:
        """Retrieves and ranks all unfinished goals by priority score."""
        goals = self.get_active_goals_with_subgoals()
        for goal in goals:
            goal["priority_score"] = self.calculate_priority_score(goal)

        # Sort descending by priority score
        goals.sort(key=lambda x: x.get("priority_score", 0.0), reverse=True)
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
