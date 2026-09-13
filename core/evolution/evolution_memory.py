# core/evolution/evolution_memory.py
import os
import json
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")


class EvolutionMemory:
    """Manages SQLite-based persistence of hypotheses, candidates, experiment ledgers, and strategy blacklists with safe rollback execution."""

    def __init__(self):
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Returns thread-safe connection to the context database."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Creates evolution-specific storage structures inside the local SQLite context database."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Table: evolution_hypotheses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_hypotheses (
                hypothesis_id TEXT PRIMARY KEY,
                trigger_event TEXT NOT NULL,
                observed_problem TEXT NOT NULL,
                degradation_metrics TEXT NOT NULL, -- Serialized JSON
                root_cause TEXT NOT NULL,
                proposed_adaptation TEXT NOT NULL, -- Serialized JSON
                predicted_outcomes TEXT NOT NULL, -- Serialized JSON
                evidence TEXT NOT NULL, -- Serialized JSON
                confidence REAL NOT NULL,
                risk_class TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('FORMULATED', 'TESTING', 'PROMOTED', 'REJECTED', 'BLACKLISTED')),
                created_at TEXT NOT NULL
            )
        """)

        # 2. Table: evolution_candidates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_candidates (
                candidate_id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL REFERENCES evolution_hypotheses(hypothesis_id),
                baseline_configuration TEXT NOT NULL, -- Serialized JSON
                candidate_configuration TEXT NOT NULL, -- Serialized JSON
                expected_benefit REAL NOT NULL,
                expected_cost INTEGER NOT NULL,
                risk_class TEXT NOT NULL CHECK (risk_class IN ('SAFE_AUTOMATIC', 'REVIEW_REQUIRED', 'HIGH_RISK')),
                resource_budget TEXT NOT NULL, -- Serialized JSON
                rollback_snapshot TEXT NOT NULL, -- Serialized JSON
                status TEXT NOT NULL CHECK (status IN ('CREATED', 'TESTING', 'PASSED', 'REJECTED', 'MONITORING', 'ROLLED_BACK'))
            )
        """)

        # 3. Table: evolution_experiments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_experiments (
                experiment_id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL REFERENCES evolution_hypotheses(hypothesis_id),
                candidate_id TEXT NOT NULL REFERENCES evolution_candidates(candidate_id),
                baseline_identifier TEXT NOT NULL,
                candidate_identifier TEXT NOT NULL,
                sample_size_target INTEGER NOT NULL,
                samples_run INTEGER DEFAULT 0,
                token_budget INTEGER NOT NULL,
                tokens_spent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELLED', 'FAILED'))
            )
        """)

        # 4. Table: evolution_strategies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_strategies (
                strategy_id TEXT PRIMARY KEY,
                task_pattern TEXT UNIQUE NOT NULL,
                configuration TEXT NOT NULL, -- Serialized JSON
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                is_blacklisted INTEGER DEFAULT 0 CHECK (is_blacklisted IN (0, 1))
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Evolution memory partitions successfully synchronized.")

    # ==============================================================================
    # HYPOTHESIS PERSISTENCE
    # ==============================================================================

    def save_hypothesis(self, h: Dict[str, Any]) -> bool:
        """Saves a structured hypothesis record to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO evolution_hypotheses (
                    hypothesis_id, trigger_event, observed_problem, degradation_metrics,
                    root_cause, proposed_adaptation, predicted_outcomes, evidence,
                    confidence, risk_class, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    h["id"], h["trigger"], h["observed_problem"],
                    json.dumps(h["degradation_metrics"]), h["root_cause"],
                    json.dumps(h["proposed_adaptation"]), json.dumps(h["predicted_outcomes"]),
                    json.dumps(h["evidence"]), h["confidence"], h["risk_class"],
                    h["status"], h["created_at"]
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save hypothesis: %s", e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a persistent hypothesis record by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_hypotheses WHERE hypothesis_id = ?", (hypothesis_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            h = dict(row)
            return {
                "id": h["hypothesis_id"],
                "trigger": h["trigger_event"],
                "observed_problem": h["observed_problem"],
                "degradation_metrics": json.loads(h["degradation_metrics"]),
                "root_cause": h["root_cause"],
                "proposed_adaptation": json.loads(h["proposed_adaptation"]),
                "predicted_outcomes": json.loads(h["predicted_outcomes"]),
                "evidence": json.loads(h["evidence"]),
                "confidence": h["confidence"],
                "risk_class": h["risk_class"],
                "status": h["status"],
                "created_at": h["created_at"]
            }
        return None

    # ==============================================================================
    # CANDIDATE PERSISTENCE
    # ==============================================================================

    def save_candidate(self, c: Dict[str, Any]) -> bool:
        """Saves a structured, immutable candidate record."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO evolution_candidates (
                    candidate_id, hypothesis_id, baseline_configuration, candidate_configuration,
                    expected_benefit, expected_cost, risk_class, resource_budget, rollback_snapshot, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["id"], c["hypothesis_id"], json.dumps(c["baseline_configuration"]),
                    json.dumps(c["candidate_configuration"]), c["expected_benefit"],
                    c["expected_cost"], c["risk_class"], json.dumps(c["resource_budget"]),
                    json.dumps(c["rollback_snapshot"]), c["status"]
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save candidate: %s", e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a persistent candidate record by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_candidates WHERE candidate_id = ?", (candidate_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            c = dict(row)
            return {
                "id": c["candidate_id"],
                "hypothesis_id": c["hypothesis_id"],
                "baseline_configuration": json.loads(c["baseline_configuration"]),
                "candidate_configuration": json.loads(c["candidate_configuration"]),
                "expected_benefit": c["expected_benefit"],
                "expected_cost": c["expected_cost"],
                "risk_class": c["risk_class"],
                "resource_budget": json.loads(c["resource_budget"]),
                "rollback_snapshot": json.loads(c["rollback_snapshot"]),
                "status": c["status"]
            }
        return None

    # ==============================================================================
    # EXPERIMENT RECORD PERSISTENCE
    # ==============================================================================

    def save_experiment_record(self, exp: Dict[str, Any]) -> bool:
        """Saves a background experiment execution ledger record."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO evolution_experiments (
                    experiment_id, hypothesis_id, candidate_id, baseline_identifier,
                    candidate_identifier, sample_size_target, samples_run, token_budget, tokens_spent, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    exp["id"], exp["hypothesis_id"], exp["candidate_id"],
                    exp["baseline_identifier"], exp["candidate_identifier"],
                    exp["sample_size_target"], exp["samples_run"],
                    exp["token_budget"], exp["tokens_spent"], exp["created_at"], exp["status"]
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save experiment record: %s", e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def get_experiment_record(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a persistent experiment record by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_experiments WHERE experiment_id = ?", (experiment_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            e = dict(row)
            return {
                "id": e["experiment_id"],
                "hypothesis_id": e["hypothesis_id"],
                "candidate_id": e["candidate_id"],
                "baseline_identifier": e["baseline_identifier"],
                "candidate_identifier": e["candidate_identifier"],
                "sample_size_target": e["sample_size_target"],
                "samples_run": e["samples_run"],
                "token_budget": e["token_budget"],
                "tokens_spent": e["tokens_spent"],
                "created_at": e["created_at"],
                "status": e["status"]
            }
        return None


# Singleton persistent layer
evo_memory_9c1 = EvolutionMemory()
