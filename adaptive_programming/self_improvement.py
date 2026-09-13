# adaptive_programming/self_improvement.py
"""
Controlled self-improvement engine — Adaptive Programming milestone.

Complete loop:
    Programming task -> experience -> weakness detection -> improvement proposal
    -> SANDBOX experiment -> benchmarks -> before/after comparison
    -> REJECT (rollback + failure experience)  or  ACCEPT (policy pipeline)

Security invariants:
  * Production code is NEVER modified during evaluation (sandbox_manager guarantees it).
  * The engine NEVER approves its own proposals. Evaluation only produces an
    evidence report; deployment goes exclusively through the existing
    proposal_manager policy pipeline, which requires human approval per
    risk class (SAFE auto-record only, CONFIRMATION_REQUIRED / HIGH_RISK gate).
"""

import logging
from typing import Dict, List, Optional

from adaptive_programming.improvement_detector import ImprovementDetector
from adaptive_programming.sandbox_manager import sandbox_manager
from adaptive_programming.experience_tracker import experience_tracker
from core.agent.proposal_manager import proposal_manager

logger = logging.getLogger("ultron-adaptive")


class SelfImprovementEngine:
    """Observes -> detects weakness -> sandboxes -> evaluates -> submits to policy."""

    # Minimum absolute benchmark gain required to call an experiment an improvement.
    MIN_IMPROVEMENT_DELTA = 0.02
    # Candidate patches touching these markers are classified HIGH_RISK.
    PROTECTED_COMPONENT_MARKERS = (
        "security", "authentication", "policy", "confirmation",
        "update", "rollback", "emergency", "token", "gateway",
    )

    def __init__(self, detector: Optional[ImprovementDetector] = None):
        self.detector = detector or ImprovementDetector()

    # ======================================================================
    # 1. OBSERVE — analyze experience for recurring weaknesses
    # ======================================================================

    def detect_weaknesses(self) -> List[Dict]:
        """Returns evidence-backed improvement proposals from recent experience."""
        proposals = self.detector.analyze()
        for p in proposals:
            logger.info("Weakness detected: skill=%s evidence=%s", p.skill, p.evidence)
        return [p.to_dict() for p in proposals]

    # ======================================================================
    # 2. SANDBOX EXPERIMENT — evaluate a candidate patch in isolation
    # ======================================================================

    def evaluate_improvement(
        self,
        skill: str,
        rel_path: str,
        old_code: str,
        new_code: str,
        timeout_seconds: int = 180,
    ) -> Dict:
        """Runs the full sandboxed before/after evaluation for one candidate patch.

        Returns an evaluation report dict. NEVER modifies production code and
        NEVER deploys anything — the caller decides whether to submit the
        report through the policy pipeline.
        """
        report: Dict = {
            "skill": skill,
            "rel_path": rel_path,
            "baseline": None,
            "candidate": None,
            "delta": 0.0,
            "regressions": [],
            "verdict": "PENDING",
        }

        # 1. Baseline measurement against the production package (read-only).
        baseline = sandbox_manager.run_benchmarks(timeout_seconds=timeout_seconds)
        if not baseline["success"]:
            report["verdict"] = "BASELINE_FAILED"
            return report
        report["baseline"] = baseline["mean_score"]

        # 2-5. Sandbox experiment and comparison (always torn down afterwards).
        sandbox = sandbox_manager.create_sandbox()
        try:
            return self._run_experiment(
                sandbox, report, rel_path,
                old_code, new_code, timeout_seconds, baseline
            )
        finally:
            # Sandbox is ALWAYS destroyed (rollback of failed experiments).
            sandbox_manager.destroy_sandbox(sandbox)

    def _run_experiment(
        self,
        sandbox,
        report,
        rel_path,
        old_code,
        new_code,
        timeout_seconds,
        baseline,
    ) -> Dict:
        applied = sandbox_manager.apply_candidate(sandbox, rel_path, old_code, new_code)
        if not applied.get("success", False):
            report["verdict"] = "PATCH_REJECTED"
            report["patch_message"] = applied.get("message", "")
            return report

        candidate = sandbox_manager.run_benchmarks(
            sandbox, timeout_seconds=timeout_seconds
        )
        if not candidate["success"]:
            report["verdict"] = "CANDIDATE_FAILED"
            return report
        report["candidate"] = candidate["mean_score"]

        # Per-benchmark regression detection.
        base_by_name = {
            r["name"]: r.get("score", 0.0) for r in baseline["results"]
        }
        for r in candidate["results"]:
            b = base_by_name.get(r["name"])
            if b is not None and r.get("score", 0.0) < b:
                report["regressions"].append({
                    "benchmark": r["name"],
                    "before": b,
                    "after": r.get("score", 0.0),
                })

        # Verdict: improvement only on measurable, regression-free gain.
        report["delta"] = round(report["candidate"] - report["baseline"], 4)
        if report["regressions"]:
            report["verdict"] = "REJECT_REGRESSION"
        elif report["delta"] >= self.MIN_IMPROVEMENT_DELTA:
            report["verdict"] = "IMPROVED"
        else:
            report["verdict"] = "NO_SIGNIFICANT_GAIN"
        return report

    # ======================================================================
    # 3. POLICY SUBMISSION — route through the EXISTING proposal pipeline
    # ======================================================================

    def _classify_risk(self, component: str, changes_behavior: bool) -> str:
        """Map a candidate change to the existing risk taxonomy."""
        lowered = component.lower()
        if any(marker in lowered for marker in self.PROTECTED_COMPONENT_MARKERS):
            return "HIGH_RISK"
        if changes_behavior:
            return "CONFIRMATION_REQUIRED"
        return "SAFE"

    def submit_for_policy(
        self, evaluation: Dict, changes_behavior: bool = True
    ) -> Optional[Dict]:
        """Submits an evaluated improvement as a change-proposal for human review.

        The engine cannot approve itself: the returned proposal starts in
        PENDING_REVIEW and is decided exclusively by the existing policy /
        approval flow (proposal_manager.submit_decision via the gateway).
        """
        if evaluation.get("verdict") != "IMPROVED":
            logger.warning(
                "Refusing to submit non-improvement (verdict=%s)",
                evaluation.get("verdict"),
            )
            return None

        risk_class = self._classify_risk(
            evaluation.get("rel_path", ""), changes_behavior
        )
        proposal = proposal_manager.create_proposal(
            title=f"Self-improvement: {evaluation['skill']}",
            reason=(
                f"Sandboxed experiment improved benchmark score "
                f"{evaluation['baseline']} -> {evaluation['candidate']} "
                f"(delta {evaluation['delta']})."
            ),
            component=f"adaptive_programming/{evaluation['rel_path']}",
            risk_class=risk_class,
            expected_impact=evaluation["skill"],
            proposed_action=(
                "Apply sandbox-validated patch after human approval; "
                "rollback available via sandbox snapshot."
            ),
            payload={
                "self_improvement": True,
                "evaluation": evaluation,
            },
            source="adaptive_programming",
            source_ref=evaluation.get("rel_path"),
        )
        if proposal:
            logger.info(
                "Self-improvement submitted to policy pipeline: %s [%s]",
                proposal["proposal_id"],
                risk_class,
            )
        return proposal

    # ======================================================================
    # 4. REJECTION LEARNING — failed experiments become failure experience
    # ======================================================================

    def record_rejection(self, evaluation: Dict, reason: str) -> None:
        """Stores a rejected/failed improvement as failure experience so the
        detector does not re-propose the same dead end.
        """
        record = experience_tracker.start_task(
            "self_improvement",
            f"Evaluate improvement for {evaluation.get('skill')}",
        )
        experience_tracker.complete_task(
            record=record,
            outcome="failed",
            tests_passed=0,
            tests_failed=0,
            iterations=1,
            details={
                "reason": reason,
                "verdict": evaluation.get("verdict"),
            },
        )
        logger.info("Rejection recorded as failure experience: %s", reason)


# Singleton instance
self_improvement_engine = SelfImprovementEngine()
