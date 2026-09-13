# adaptive_programming/experience_tracker.py
"""
Programming experience tracker — records structured outcomes.

Reuses the existing memory_manager episodic/strategy memory for persistence.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

try:
    from core.context.memory_manager import memory_manager
except Exception:
    memory_manager = None


class ExperienceRecord:
    """A single programming task experience."""

    def __init__(self, task_type: str, description: str, language: str = "python"):
        self.record_id = f"exp_{uuid.uuid4().hex[:8]}"
        self.task_type = task_type
        self.description = description
        self.language = language
        self.files_affected: List[str] = []
        self.strategy_used = ""
        self.errors_encountered: List[str] = []
        self.tests_passed = 0
        self.tests_failed = 0
        self.iterations = 0
        self.duration_sec = 0.0
        self.rollback_events = 0
        self.outcome = "unknown"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata: Dict = {}

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "task_type": self.task_type,
            "description": self.description,
            "language": self.language,
            "files_affected": self.files_affected,
            "strategy_used": self.strategy_used,
            "errors_encountered": self.errors_encountered,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "iterations": self.iterations,
            "duration_sec": round(self.duration_sec, 1),
            "rollback_events": self.rollback_events,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
        }


class ExperienceTracker:
    """Tracks and persists programming experiences."""

    def __init__(self):
        self._recent: List[ExperienceRecord] = []

    def start_task(self, task_type: str, description: str,
                   language: str = "python") -> ExperienceRecord:
        """Begin tracking a new programming task."""
        record = ExperienceRecord(task_type, description, language)
        logger.info("Experience tracking started: %s — %s", task_type, description)
        return record

    def complete_task(self, record: ExperienceRecord, outcome: str,
                      persist: bool = True):
        """Finalize a task and optionally persist to memory."""
        record.outcome = outcome
        self._recent.append(record)

        if persist and memory_manager:
            try:
                memory_manager.add_episodic_memory(
                    user_prompt=record.description,
                    parsed_intent=f"coding:{record.task_type}",
                    actual_results=f"Outcome: {outcome}; "
                                  f"tests={record.tests_passed}/{record.tests_passed + record.tests_failed}; "
                                  f"iterations={record.iterations}; "
                                  f"files={','.join(record.files_affected)}",
                    success_status=(outcome == "success"),
                    resource_latency_sec=record.duration_sec,
                )
            except Exception as e:
                logger.warning("Failed to persist experience: %s", e)

        logger.info("Experience recorded: %s — outcome=%s", record.description, outcome)

    def get_recent_experiences(self, limit: int = 20) -> List[Dict]:
        return [r.to_dict() for r in self._recent[-limit:]]

    def get_failure_patterns(self) -> Dict[str, int]:
        """Count failure types across recent experiences."""
        patterns: Dict[str, int] = {}
        for record in self._recent:
            if record.outcome != "success":
                key = record.task_type
                patterns[key] = patterns.get(key, 0) + 1
        return patterns

    def get_statistics(self) -> Dict:
        """Aggregate statistics across all recent experiences."""
        total = len(self._recent)
        solved = sum(1 for r in self._recent if r.outcome == "success")
        return {
            "total_tasks": total,
            "solved": solved,
            "failed": total - solved,
            "success_rate": round(solved / max(1, total), 3),
            "total_iterations": sum(r.iterations for r in self._recent),
            "total_tests_passed": sum(r.tests_passed for r in self._recent),
            "total_tests_failed": sum(r.tests_failed for r in self._recent),
            "total_rollbacks": sum(r.rollback_events for r in self._recent),
        }


experience_tracker = ExperienceTracker()
