# adaptive_programming/improvement_detector.py
"""
Detects recurring weaknesses from programming experience.
Generates improvement proposals fed into the existing evolution pipeline.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

from adaptive_programming.capability_registry import capability_registry
from adaptive_programming.experience_tracker import experience_tracker


class ImprovementProposal:
    """A proposed self-improvement derived from evidence."""

    def __init__(self, skill: str, evidence: str, expected_benefit: str):
        self.proposal_id = f"imp_{uuid.uuid4().hex[:8]}"
        self.skill = skill
        self.evidence = evidence
        self.expected_benefit = expected_benefit
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "proposed"  # proposed -> sandbox -> evaluated -> approved/rejected

    def to_dict(self) -> Dict:
        return {
            "proposal_id": self.proposal_id,
            "skill": self.skill,
            "evidence": self.evidence,
            "expected_benefit": self.expected_benefit,
            "created_at": self.created_at,
            "status": self.status,
        }


class ImprovementDetector:
    """Analyzes experience to detect weaknesses and propose improvements."""

    def __init__(self, weakness_threshold: float = 0.6, min_attempts: int = 3,
                 registry: Optional["CapabilityRegistry"] = None):
        self.weakness_threshold = weakness_threshold
        self.min_attempts = min_attempts
        # Injectable registry allows sandboxed evaluation against in-memory
        # datasets without touching the persisted skills registry.
        self.registry = registry if registry is not None else capability_registry

    def analyze(self) -> List[ImprovementProposal]:
        """Run analysis and return proposals for detected weaknesses."""
        proposals = []
        weakest = self.registry.get_weakest_skills(limit=10)

        for skill_data in weakest:
            if skill_data["success_rate"] < self.weakness_threshold:
                proposal = ImprovementProposal(
                    skill=skill_data["skill"],
                    evidence=f"Success rate {skill_data['success_rate']:.0%} over "
                             f"{skill_data['tasks_attempted']} tasks "
                             f"(avg {skill_data['average_iterations']} iterations). "
                             f"Regressions: {skill_data['regressions_introduced']}.",
                    expected_benefit=f"Reduce failure rate for {skill_data['skill']} tasks "
                                     f"and decrease average iterations needed.",
                )
                proposals.append(proposal)
                logger.info("Improvement proposal generated: %s", skill_data["skill"])

        return proposals

    def get_evidence_summary(self) -> Dict:
        """Return summary of current capability strengths/weaknesses."""
        stats = experience_tracker.get_statistics()
        weakest = capability_registry.get_weakest_skills(limit=3)
        strongest = capability_registry.get_strongest_skills(limit=3)
        return {
            "overall": stats,
            "weakest_skills": weakest,
            "strongest_skills": strongest,
            "failure_patterns": experience_tracker.get_failure_patterns(),
        }
