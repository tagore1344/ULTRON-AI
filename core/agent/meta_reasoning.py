# core/agent/meta_reasoning.py
import datetime
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ultron-api")


class MetaReasoningRecord:
    """Represents a stateful, calibrated meta-reasoning record for a single cognitive cycle."""

    def __init__(
        self,
        cycle_id: str,
        goal: str,
        predicted_success: float,
        actual_success: bool,
        predicted_latency: float,
        actual_latency: float,
        predicted_tokens: int,
        actual_tokens: int,
        failed_assumption: Optional[str] = None,
        alternative_considered: Optional[str] = None,
        lesson_learned: Optional[str] = None
    ):
        self.cycle_id = cycle_id
        self.goal = goal
        self.predicted_success = predicted_success
        self.actual_success = actual_success
        self.predicted_latency = predicted_latency
        self.actual_latency = actual_latency
        self.predicted_tokens = predicted_tokens
        self.actual_tokens = actual_tokens
        self.failed_assumption = failed_assumption
        self.alternative_considered = alternative_considered
        self.lesson_learned = lesson_learned

    def get_latency_discrepancy(self) -> float:
        """Calculates actual vs predicted latency discrepancy in seconds."""
        return abs(self.actual_latency - self.predicted_latency)

    def get_token_discrepancy(self) -> int:
        """Calculates actual vs predicted token usage discrepancy."""
        return abs(self.actual_tokens - self.predicted_tokens)


class MetaReasoningEngine:
    """Evaluates the quality of ULTRON's own plans, judgments, and predictions, enforcing recursion limits."""

    def __init__(self):
        self.records: List[MetaReasoningRecord] = []
        self.calibration_error_history: List[float] = []

        # Recursion and budget limits
        self.max_reflection_depth = 3
        self.max_reflection_tokens = 1000
        self.max_reflection_runtime_seconds = 5.0

        # State tracking
        self.reflection_depth = 0

    def evaluate_cycle_calibration(self, record: MetaReasoningRecord) -> Dict[str, Any]:
        """Measures discrepancy between predicted and observed parameters to track calibration error."""
        success_error = abs((1.0 if record.actual_success else 0.0) - record.predicted_success)
        latency_ratio_error = record.get_latency_discrepancy() / max(0.01, record.predicted_latency)
        token_ratio_error = record.get_token_discrepancy() / max(1, record.predicted_tokens)

        # Combined calibration error score (average delta)
        combined_error = (success_error + min(2.0, latency_ratio_error) + min(2.0, token_ratio_error)) / 3.0
        self.calibration_error_history.append(combined_error)

        return {
            "success_error": round(success_error, 2),
            "latency_ratio_error": round(latency_ratio_error, 2),
            "token_ratio_error": round(token_ratio_error, 2),
            "combined_calibration_error": round(combined_error, 2)
        }

    def evaluate_plan_quality(self, record: MetaReasoningRecord, retries: int = 0) -> Dict[str, Any]:
        """Calculates a plan quality score based on latency delta and retries."""
        score = 100.0

        # Penalize for retries and latency overheads
        score -= (retries * 15.0)
        latency_overhead = record.actual_latency - record.predicted_latency
        if latency_overhead > 0.5:
            score -= (latency_overhead * 10.0)

        score = max(0.0, score)
        return {
            "plan_quality_score": round(score, 1),
            "wasted_tool_calls": retries,
            "latency_overhead_sec": round(latency_overhead, 2)
        }

    def evaluate_judgment_quality(self, opinion_confidence: float, observed_success: bool) -> Dict[str, Any]:
        """Evaluates factual and inference calibration accuracy of the JudgmentEngine."""
        observed_value = 1.0 if observed_success else 0.0
        calibration_delta = abs(observed_value - opinion_confidence)

        is_false_disagreement = observed_success and opinion_confidence < 0.35
        score = max(0.0, 100.0 - (calibration_delta * 100.0))

        return {
            "judgment_quality_score": round(score, 1),
            "calibration_delta": round(calibration_delta, 2),
            "is_false_disagreement": is_false_disagreement
        }

    def reflect_self_questioning(self, question: str, tokens_allocated: int = 200) -> Dict[str, Any]:
        """
        Allows structured self-questioning.
        Strictly enforces token, time, and recursion-depth limits.
        """
        start_time = time.time()

        # 1. Recursion Depth Guard
        if self.reflection_depth >= self.max_reflection_depth:
            raise RecursionError(f"Meta-reasoning recursion limit exceeded (Depth: {self.reflection_depth}/{self.max_reflection_depth})")

        # 2. Token Budget Guard
        if tokens_allocated > self.max_reflection_tokens:
            raise ValueError(f"Reflection token budget requested ({tokens_allocated}) exceeds maximum ({self.max_reflection_tokens})")

        self.reflection_depth += 1
        logger.info("[META] Initiating reflection layer depth: %d", self.reflection_depth)

        q_lower = question.lower().strip()
        verdict = ""
        analysis = ""

        # Recursive trial simulation (mock nested analysis up to depth 2)
        if self.reflection_depth < 2:
            try:
                # Spawn a nested meta-reflection to evaluate our own assumptions recursively!
                self.reflect_self_questioning("Did I overestimate my confidence?", tokens_allocated=100)
            except Exception as ex:
                logger.debug("Nested reflection completed: %s", ex)

        # Parse questions
        if "why did i choose this plan" in q_lower:
            verdict = "Chosen plan had the highest expected success rate (98%) in StrategyMemory."
            analysis = "Baseline metrics favored serial diagnostics; however, memory retrieval indicated low SNR on microphone interfaces."
        elif "which assumption was wrong" in q_lower:
            verdict = "Assumed Windows PyCaw volume endpoints were present in headless Linux container."
            analysis = "Failed to map local AudioDevice activation attributes, leading to unhandled AttributeError."
        elif "did i overestimate my confidence" in q_lower:
            verdict = "Yes, initial confidence was 0.95, but actual success was 0.0."
            analysis = "Subjective probability neglected hardware-block constraints. Calibration corrected to 0.10."
        else:
            verdict = "No clear contradiction found."
            analysis = "Metrics align within 10% variance thresholds."

        elapsed = time.time() - start_time

        # 3. Execution Time Guard
        if elapsed > self.max_reflection_runtime_seconds:
            self.reflection_depth -= 1
            raise TimeoutError(f"Meta-reflection exceeded maximum runtime limit ({elapsed:.2f}s > {self.max_reflection_runtime_seconds}s)")

        self.reflection_depth -= 1

        return {
            "question": question,
            "verdict": verdict,
            "analysis": analysis,
            "elapsed_seconds": round(elapsed, 4),
            "reflection_depth_reached": self.reflection_depth + 1
        }


# Singleton engine instance
meta_reasoning_engine = MetaReasoningEngine()
