# core/context/memory_manager.py
import os
import re
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")


def sanitize_sensitive_data(text: str) -> str:
    """Strips API keys, bearer tokens, passwords, and sensitive tokens to preserve the security perimeter."""
    if not isinstance(text, str):
        return text
    # 1. Redact Bearer tokens
    text = re.sub(r'(?i)bearer\s+[a-zA-Z0-9_\-\.]+', 'Bearer <REDACTED_TOKEN>', text)
    # 2. Redact OpenAI / Google keys
    text = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-<REDACTED_OPENAI_KEY>', text)
    text = re.sub(r'AIzaSy[a-zA-Z0-9_\-]{33}', 'AIzaSy<REDACTED_GOOGLE_KEY>', text)
    # 3. Redact explicit assignments
    text = re.sub(r'(?i)(password|passphrase|secret|key|token|auth_token|access_token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\@]+["\']?', r'\1=<REDACTED>', text)
    return text


class MemoryManager:
    """Manages separate context partitions (working, episodic, semantic, strategy, failure) statefully."""

    def __init__(self):
        self.working_memory: Dict[str, Any] = {}
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Returns thread-safe connection to the context database."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Creates the context database and schemas if not already initialized."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Episodic Memory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                memory_id TEXT PRIMARY KEY,
                goal_id TEXT,
                timestamp TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                parsed_intent TEXT NOT NULL,
                actual_results TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                success_status INTEGER NOT NULL CHECK (success_status IN (0, 1)),
                resource_tokens_spent INTEGER,
                resource_latency_sec REAL,
                importance_score REAL DEFAULT 0.0
            )
        """)

        # 2. Semantic Memory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                knowledge_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                keywords TEXT NOT NULL,
                content TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_frequency INTEGER DEFAULT 1
            )
        """)

        # 3. Strategy Memory (Experience Store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_memory (
                strategy_id TEXT PRIMARY KEY,
                task_pattern TEXT UNIQUE NOT NULL,
                successful_dag_structure TEXT NOT NULL,
                failed_attempts_count INTEGER DEFAULT 0,
                successful_runs_count INTEGER DEFAULT 0,
                average_latency REAL,
                last_run_timestamp TEXT NOT NULL
            )
        """)

        # 4. Failure Memory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_memory (
                failure_id TEXT PRIMARY KEY,
                task_pattern TEXT NOT NULL,
                failed_node_intent TEXT NOT NULL,
                error_signature TEXT NOT NULL,
                recovery_decision_applied TEXT NOT NULL,
                context_snapshot TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        # 5. Evolution Memory (Schema only; self-evolution disabled)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_memory (
                experiment_id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL,
                status TEXT NOT NULL,
                metric_delta REAL,
                timestamp TEXT NOT NULL
            )
        """)

        conn.commit()

        # Schema Migration: Add importance_score if missing from prior legacy tables
        try:
            cursor.execute("ALTER TABLE episodic_memory ADD COLUMN importance_score REAL DEFAULT 0.0")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Already has the column from Phase 10.2 schema

        conn.close()
        logger.info("Context database successfully initialized at: %s", DB_PATH)

    # ==============================================================================
    # WORKING MEMORY (In-Memory Transient Context)
    # ==============================================================================

    def update_working_memory(self, key: str, value: Any):
        """Stores transient execution state in Working Memory."""
        self.working_memory[key] = value

    def clear_working_memory(self):
        """Clears transient working variables."""
        self.working_memory.clear()

    # ==============================================================================
    # WRITE INTERFACES (With Pre-write Sanitization & Retention Enforcement)
    # ==============================================================================

    def add_episodic_memory(
        self,
        user_prompt: str,
        parsed_intent: str,
        actual_results: str,
        success_status: bool,
        confidence_score: float = 0.95,
        resource_tokens_spent: int = 500,
        resource_latency_sec: float = 0.1,
        goal_id: Optional[str] = None
    ) -> str:
        """Saves a single episodic memory cleanly after execution."""
        memory_id = f"mem_{uuid_hex()}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

        # Sanitize sensitive fields
        sanitized_prompt = sanitize_sensitive_data(user_prompt)
        sanitized_results = sanitize_sensitive_data(actual_results)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO episodic_memory (
                memory_id, goal_id, timestamp, user_prompt, parsed_intent,
                actual_results, confidence_score, success_status,
                resource_tokens_spent, resource_latency_sec, importance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0)
            """,
            (
                memory_id, goal_id, timestamp, sanitized_prompt, parsed_intent,
                sanitized_results, confidence_score, 1 if success_status else 0,
                resource_tokens_spent, resource_latency_sec
            )
        )
        conn.commit()

        # Enforce retention limit (max 5000 records)
        cursor.execute("SELECT COUNT(*) FROM episodic_memory")
        count = cursor.fetchone()[0]
        if count > 5000:
            cursor.execute(
                """
                DELETE FROM episodic_memory WHERE memory_id IN (
                    SELECT memory_id FROM episodic_memory ORDER BY timestamp ASC LIMIT ?
                )
                """,
                (count - 5000,)
            )
            conn.commit()

        conn.close()
        return memory_id

    def add_semantic_memory(self, category: str, keywords: str, content: str) -> str:
        """Registers a fact or learned system pattern into Semantic Memory."""
        knowledge_id = f"know_{uuid_hex()}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

        # Sanitize sensitive fields
        sanitized_content = sanitize_sensitive_data(content)
        sanitized_keywords = sanitize_sensitive_data(keywords)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO semantic_memory (
                knowledge_id, category, keywords, content, last_accessed, access_frequency
            ) VALUES (?, ?, ?, ?, ?, 1)
            """,
            (knowledge_id, category, sanitized_keywords, sanitized_content, timestamp)
        )
        conn.commit()
        conn.close()
        return knowledge_id

    def add_strategy_memory(
        self,
        task_pattern: str,
        successful_dag_structure: str,
        failed_attempts_count: int = 0,
        successful_runs_count: int = 1,
        average_latency: float = 0.2
    ) -> str:
        """Registers or updates a successful execution strategy path."""
        strategy_id = f"strat_{uuid_hex()}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO strategy_memory (
                    strategy_id, task_pattern, successful_dag_structure,
                    failed_attempts_count, successful_runs_count, average_latency, last_run_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_pattern) DO UPDATE SET
                    successful_runs_count = successful_runs_count + 1,
                    failed_attempts_count = failed_attempts_count + EXCLUDED.failed_attempts_count,
                    average_latency = (average_latency + EXCLUDED.average_latency) / 2.0,
                    last_run_timestamp = EXCLUDED.last_run_timestamp
                """,
                (
                    strategy_id, task_pattern, successful_dag_structure,
                    failed_attempts_count, successful_runs_count, average_latency, timestamp
                )
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to commit strategy memory: %s", e)
        finally:
            conn.close()
        return strategy_id

    def add_failure_memory(
        self,
        task_pattern: str,
        failed_node_intent: str,
        error_signature: str,
        recovery_decision_applied: str,
        context_snapshot: str
    ) -> str:
        """Logs a failure signature for contextual awareness and re-planning avoidance."""
        failure_id = f"fail_{uuid_hex()}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

        sanitized_error = sanitize_sensitive_data(error_signature)
        sanitized_context = sanitize_sensitive_data(context_snapshot)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO failure_memory (
                failure_id, task_pattern, failed_node_intent,
                error_signature, recovery_decision_applied, context_snapshot, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                failure_id, task_pattern, failed_node_intent,
                sanitized_error, recovery_decision_applied, sanitized_context, timestamp
            )
        )
        conn.commit()

        # Enforce retention limit (max 200 failure logs per pattern)
        cursor.execute("SELECT COUNT(*) FROM failure_memory WHERE task_pattern = ?", (task_pattern,))
        count = cursor.fetchone()[0]
        if count > 200:
            cursor.execute(
                """
                DELETE FROM failure_memory WHERE failure_id IN (
                    SELECT failure_id FROM failure_memory WHERE task_pattern = ?
                    ORDER BY timestamp ASC LIMIT ?
                )
                """,
                (task_pattern, count - 200)
            )
            conn.commit()

        conn.close()
        return failure_id

    # ==============================================================================
    # MULTI-CRITERIA RETRIEVAL ENGINE (Relevance + Recency + Frequency)
    # ==============================================================================

    def get_relevant_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves matching context blocks from episodic, semantic, strategy, and failure partitions.
        Scores results dynamically using Relevance, Recency, and Frequency constraints.
        """
        results = []
        words = [w.lower() for w in query.split() if len(w) > 2]
        if not words:
            return []

        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Fetch Episodic Memories
        cursor.execute("SELECT * FROM episodic_memory")
        for row in cursor.fetchall():
            row_dict = dict(row)
            text_target = f"{row_dict['user_prompt']} {row_dict['parsed_intent']} {row_dict['actual_results']}".lower()

            # Relevance: Token matching frequency
            relevance = sum(text_target.count(w) for w in words)
            if relevance == 0:
                continue

            # Recency Weighting
            try:
                dt = datetime.datetime.fromisoformat(row_dict["timestamp"].replace("Z", ""))
                age_days = (datetime.datetime.now() - dt).days
                recency = 1.0 / (age_days + 1.1)
            except:
                recency = 0.5

            # Combine Score
            score = (relevance * 1.5) + (recency * 2.0)
            row_dict["score"] = score
            row_dict["source_partition"] = "Episodic"
            results.append(row_dict)

        # 2. Fetch Semantic Memories
        cursor.execute("SELECT * FROM semantic_memory")
        for row in cursor.fetchall():
            row_dict = dict(row)
            text_target = f"{row_dict['keywords']} {row_dict['content']}".lower()

            relevance = sum(text_target.count(w) for w in words)
            if relevance == 0:
                continue

            frequency = row_dict["access_frequency"]
            score = (relevance * 2.0) + (frequency * 0.1)
            row_dict["score"] = score
            row_dict["source_partition"] = "Semantic"
            results.append(row_dict)

        # 3. Fetch Strategy Memories (Experience Store)
        cursor.execute("SELECT * FROM strategy_memory")
        for row in cursor.fetchall():
            row_dict = dict(row)
            text_target = row_dict["task_pattern"].lower()

            relevance = sum(text_target.count(w) for w in words)
            if relevance == 0:
                continue

            runs = row_dict["successful_runs_count"]
            failures = row_dict["failed_attempts_count"]
            score = (relevance * 3.0) + (runs * 0.5) - (failures * 0.3)
            row_dict["score"] = score
            row_dict["source_partition"] = "Strategy"
            results.append(row_dict)

        # 4. Fetch Failure Memories
        cursor.execute("SELECT * FROM failure_memory")
        for row in cursor.fetchall():
            row_dict = dict(row)
            text_target = f"{row_dict['task_pattern']} {row_dict['failed_node_intent']} {row_dict['error_signature']}".lower()

            relevance = sum(text_target.count(w) for w in words)
            if relevance == 0:
                continue

            score = relevance * 1.2
            row_dict["score"] = score
            row_dict["source_partition"] = "Failure"
            results.append(row_dict)

        conn.close()

        # Sort and select top matches
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return results[:limit]

    # ==============================================================================
    # RESET AND CLEAR CONTROL
    # ==============================================================================

    def clear_all_context_memory(self):
        """Safely clears all persistent and working memory pools."""
        self.clear_working_memory()

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM episodic_memory")
        cursor.execute("DELETE FROM semantic_memory")
        cursor.execute("DELETE FROM strategy_memory")
        cursor.execute("DELETE FROM failure_memory")
        cursor.execute("DELETE FROM evolution_memory")
        conn.commit()
        conn.close()
        logger.warning("Contextual memory completely reset and cleared.")


# Helper to generate unique hex strings securely
def uuid_hex() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


# Singleton instance of the MemoryManager
memory_manager = MemoryManager()
