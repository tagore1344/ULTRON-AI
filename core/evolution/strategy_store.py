# core/evolution/strategy_store.py
import json
import logging
from typing import Dict, Any, Optional

from core.evolution.evolution_memory import evo_memory_9c1

logger = logging.getLogger("ultron-api")


class StrategyStore:
    """Manages active, promoted, and blacklisted strategies statefully inside memory and SQLite."""

    def __init__(self):
        self.active_strategies_cache: Dict[str, Dict[str, Any]] = {}

    def is_blacklisted(self, task_pattern: str) -> bool:
        """Queries the blacklist state of a task pattern to prevent infinite re-discovery."""
        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_blacklisted FROM evolution_strategies WHERE task_pattern = ?", (task_pattern,))
            row = cursor.fetchone()
            if row:
                return bool(row["is_blacklisted"])
        except Exception as e:
            logger.error("Failed to query blacklist strategy: %s", e)
        finally:
            conn.close()
        return False

    def blacklist_strategy(self, task_pattern: str):
        """Puts a task pattern directly onto the blacklist to prevent future trials."""
        import uuid
        strategy_id = f"strat_{uuid.uuid4().hex[:12]}"
        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO evolution_strategies (strategy_id, task_pattern, configuration, is_blacklisted)
                VALUES (?, ?, '{}', 1)
                ON CONFLICT(task_pattern) DO UPDATE SET is_blacklisted = 1
                """,
                (strategy_id, task_pattern)
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to blacklist strategy: %s", e)
            try:
                conn.rollback()
            except:
                pass
        finally:
            conn.close()
        logger.warning("Strategy task pattern '%s' has been blacklisted from future self-evolution.", task_pattern)

    def get_strategy_config(self, task_pattern: str) -> Optional[Dict[str, Any]]:
        """Retrieves the active, successfully promoted configuration for a task pattern."""
        if task_pattern in self.active_strategies_cache:
            return self.active_strategies_cache[task_pattern]

        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT configuration FROM evolution_strategies WHERE task_pattern = ? AND is_blacklisted = 0", (task_pattern,))
            row = cursor.fetchone()
            if row:
                config = json.loads(row["configuration"])
                self.active_strategies_cache[task_pattern] = config
                return config
        except Exception as e:
            logger.error("Failed to parse strategy configuration for '%s': %s", task_pattern, e)
        finally:
            conn.close()
        return None

    def save_strategy(self, task_pattern: str, config: Dict[str, Any], success: bool):
        """Saves or updates a successfully evaluated execution strategy."""
        import uuid
        strategy_id = f"strat_{uuid.uuid4().hex[:12]}"
        config_str = json.dumps(config)

        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO evolution_strategies (
                    strategy_id, task_pattern, configuration, success_count, failure_count, is_blacklisted
                ) VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(task_pattern) DO UPDATE SET
                    configuration = EXCLUDED.configuration,
                    success_count = success_count + ?,
                    failure_count = failure_count + ?
                """,
                (
                    strategy_id, task_pattern, config_str,
                    1 if success else 0, 0 if success else 1,
                    1 if success else 0, 0 if success else 1
                )
            )
            conn.commit()
            self.active_strategies_cache[task_pattern] = config
            logger.info("Successfully updated strategy mapping in StrategyStore for pattern '%s'", task_pattern)
        except Exception as e:
            logger.error("Failed to save strategy: %s", e)
            try:
                conn.rollback()
            except:
                pass
        finally:
            conn.close()


strategy_store_9c1 = StrategyStore()
