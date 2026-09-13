# adaptive_programming/capability_registry.py
"""
Programming capability registry — evidence-based skill tracking.

Stores real metrics derived from actual evaluated tasks.
Reuses the existing memory_manager persistence layer.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

# ULTRON_REPO_ROOT lets a sandboxed copy of this package keep targeting the real
# repository for benchmark verification (sandbox isolation support).
REPO_ROOT = Path(__file__.replace("\\", "/")).resolve().parent.parent
import os as _os
if _os.environ.get("ULTRON_REPO_ROOT"):
    REPO_ROOT = Path(_os.environ["ULTRON_REPO_ROOT"])
SKILLS_DIR = REPO_ROOT / "backend" / "data" / "adaptive_programming"


class SkillMetrics:
    """Evidence-based metrics for a single skill."""

    def __init__(self, skill: str):
        self.skill = skill
        self.tasks_attempted = 0
        self.tasks_solved = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.regressions_introduced = 0
        self.total_iterations = 0
        self.total_duration_sec = 0.0
        self.last_updated = ""

    @property
    def success_rate(self) -> float:
        return self.tasks_solved / max(1, self.tasks_attempted)

    @property
    def average_iterations(self) -> float:
        return self.total_iterations / max(1, self.tasks_attempted)

    def to_dict(self) -> Dict:
        return {
            "skill": self.skill,
            "tasks_attempted": self.tasks_attempted,
            "tasks_solved": self.tasks_solved,
            "success_rate": round(self.success_rate, 3),
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "regressions_introduced": self.regressions_introduced,
            "average_iterations": round(self.average_iterations, 1),
            "total_duration_sec": round(self.total_duration_sec, 1),
            "last_updated": self.last_updated,
        }


class CapabilityRegistry:
    """Registry of programming capabilities with evidence-based metrics."""

    def __init__(self):
        self._skills: Dict[str, SkillMetrics] = {}
        self._load()

    def _load(self):
        """Load persisted skill metrics."""
        path = SKILLS_DIR / "skills.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for skill_name, metrics in data.items():
                    s = SkillMetrics(skill_name)
                    s.tasks_attempted = metrics.get("tasks_attempted", 0)
                    s.tasks_solved = metrics.get("tasks_solved", 0)
                    s.tests_passed = metrics.get("tests_passed", 0)
                    s.tests_failed = metrics.get("tests_failed", 0)
                    s.regressions_introduced = metrics.get("regressions_introduced", 0)
                    s.total_iterations = metrics.get("total_iterations", 0)
                    s.total_duration_sec = metrics.get("total_duration_sec", 0.0)
                    s.last_updated = metrics.get("last_updated", "")
                    self._skills[skill_name] = s
            except Exception as e:
                logger.warning("Failed to load skill registry: %s", e)

    def _save(self):
        """Persist skill metrics to disk."""
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        path = SKILLS_DIR / "skills.json"
        data = {name: s.to_dict() for name, s in self._skills.items()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record_task(self, skill: str, solved: bool, tests_passed: int = 0,
                    tests_failed: int = 0, iterations: int = 1,
                    duration_sec: float = 0.0, regressions: int = 0):
        """Record the outcome of a task for a skill."""
        s = self._skills.setdefault(skill, SkillMetrics(skill))
        s.tasks_attempted += 1
        if solved:
            s.tasks_solved += 1
        s.tests_passed += tests_passed
        s.tests_failed += tests_failed
        s.total_iterations += iterations
        s.total_duration_sec += duration_sec
        s.regressions_introduced += regressions
        s.last_updated = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_skill(self, skill: str) -> Optional[SkillMetrics]:
        return self._skills.get(skill)

    def get_all_skills(self) -> List[Dict]:
        return [s.to_dict() for s in self._skills.values()]

    def get_weakest_skills(self, limit: int = 5) -> List[Dict]:
        """Return skills with lowest success rate (minimum 3 attempts)."""
        qualified = [s for s in self._skills.values() if s.tasks_attempted >= 3]
        qualified.sort(key=lambda s: s.success_rate)
        return [s.to_dict() for s in qualified[:limit]]

    def get_strongest_skills(self, limit: int = 5) -> List[Dict]:
        """Return skills with highest success rate."""
        qualified = [s for s in self._skills.values() if s.tasks_attempted >= 3]
        qualified.sort(key=lambda s: s.success_rate, reverse=True)
        return [s.to_dict() for s in qualified[:limit]]


capability_registry = CapabilityRegistry()
