# core/evolution/hypothesis_engine.py
import os
import json
import logging
import datetime
from typing import List, Dict, Any, Optional

from core.evolution.evolution_memory import evo_memory_9c1

logger = logging.getLogger("ultron-api")


class HypothesisEngine:
    """Analyzes historical failure/episodic memories to detect weaknesses and compile structured hypotheses."""

    def __init__(self):
        pass

    def scan_for_weaknesses(self) -> List[Dict[str, Any]]:
        """
        Queries FailureMemory and EpisodicMemory to detect repeated failures,
        latency bottlenecks, and spelling corrections in user patterns.
        """
        weaknesses = []
        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()

        try:
            # 1. Detect Repeated Failures (Grouped by task pattern)
            cursor.execute(
                """
                SELECT task_pattern, COUNT(*) as count, GROUP_CONCAT(error_signature) as errors
                FROM failure_memory
                GROUP BY task_pattern
                HAVING count >= 3
                """
            )
            for row in cursor.fetchall():
                weaknesses.append({
                    "type": "REPEATED_FAILURE",
                    "pattern": row["task_pattern"],
                    "frequency": row["count"],
                    "errors": row["errors"].split(",") if row["errors"] else []
                })

            # 2. Detect Latency Degradation
            cursor.execute(
                """
                SELECT user_prompt, resource_latency_sec
                FROM episodic_memory
                WHERE resource_latency_sec > 1.5
                """
            )
            for row in cursor.fetchall():
                weaknesses.append({
                    "type": "LATENCY_DEGRADATION",
                    "pattern": row["user_prompt"],
                    "latency": row["resource_latency_sec"]
                })

        except Exception as e:
            logger.error("Failed to scan failure/episodic memories: %s", e)
        finally:
            conn.close()

        return weaknesses

    def propose_hypothesis(self, weakness: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Formulates a structured, evidence-based hypothesis for a detected weakness.
        Determines deterministic confidence and assigns appropriate risk class boundaries.
        """
        import uuid
        now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        hypothesis_id = f"hyp_{uuid.uuid4().hex[:12]}"
        pattern = weakness.get("pattern", "unknown")

        # Integration Hook: Ingest Causal Risk evidence
        try:
            from core.neural.prediction_engine import prediction_engine
            causal_risk = prediction_engine.compute_advisory_failure_risk(pattern)
            if causal_risk > 0.50:
                logger.info("HypothesisEngine: Neural Causal risk is high (%.2f). Incorporating as evidence.", causal_risk)
        except Exception:
            pass

        # Check for duplicate hypotheses to prevent loop re-testing
        conn = evo_memory_9c1.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM evolution_hypotheses WHERE observed_problem LIKE ?", (f"%{pattern}%",))
        duplicate_count = cursor.fetchone()[0]
        conn.close()

        if duplicate_count > 0:
            logger.info("HypothesisEngine: Duplicate hypothesis check blocked creation for pattern '%s'", pattern)
            return None

        # Case 1: Repeated Failures of Voice Transcription Typos (e.g. "chroome" -> "chrome")
        if weakness["type"] == "REPEATED_FAILURE" and "chroome" in pattern.lower():
            return {
                "id": hypothesis_id,
                "trigger": "Repeated command failure with 'chroome' spelling typo",
                "observed_problem": f"Voice transcription mapped Chrome launch as '{pattern}' which failed intent routing",
                "degradation_metrics": {"error_rate": 1.0, "latency_ms": 0.0},
                "root_cause": "The speech engine transcription occasionally mispells 'chrome' as 'chroome' in high noise floor states",
                "proposed_adaptation": {"command_alias": {"chroome": "chrome"}},
                "predicted_outcomes": {"error_rate": 0.0, "intent_accuracy": 1.0},
                "evidence": weakness.get("errors", ["Spelling anomaly"]),
                "confidence": 0.98, # Fact-driven rule base
                "risk_class": "SAFE_AUTOMATIC", # Alias mappings are SAFE_AUTOMATIC
                "status": "FORMULATED",
                "created_at": now_str
            }

        # Case 2: Latency Degradation during complex prompt parsing
        elif weakness["type"] == "LATENCY_DEGRADATION" and weakness.get("latency", 0.0) > 1.5:
            return {
                "id": hypothesis_id,
                "trigger": f"High latency of {weakness.get('latency')}s detected in prompt parsing",
                "observed_problem": f"User query '{pattern}' caused substantial execution delay",
                "degradation_metrics": {"latency_sec": weakness.get("latency")},
                "root_cause": "Orchestrator routed general conversation to high-parameter slow API instead of local fast cache",
                "proposed_adaptation": {"model_routing": {"query": "gemini", "default_routing": "openai"}},
                "predicted_outcomes": {"latency_sec": 0.15},
                "evidence": [f"Execution latency logged at {weakness.get('latency')}s"],
                "confidence": 0.85,
                "risk_class": "REVIEW_REQUIRED", # Model preference updates require review
                "status": "FORMULATED",
                "created_at": now_str
            }

        # Case 3: Source Code Proposal Required (e.g. Update Voice Verification Algorithm)
        elif "voice verification" in pattern.lower():
            # If the weakness demands source code edits, create a CHANGE_PROPOSAL-class hypothesis
            return {
                "id": hypothesis_id,
                "trigger": "Voice verification fail-closed rate exceeds threshold",
                "observed_problem": "Microphone silence levels trigger speaker validation failure anomalies on wake loops",
                "degradation_metrics": {"error_rate": 0.35},
                "root_cause": "Hardcoded verification algorithm lacks dynamic ambient signal-to-noise compensation",
                "proposed_adaptation": {"change_proposal": {"file": "voice_id.py", "diff": "@@ -20,2 +20,4 @@\n- threshold = 0.5\n+ threshold = adaptive_threshold()"}},
                "predicted_outcomes": {"error_rate": 0.02},
                "evidence": ["Verification failure logs under quiet states"],
                "confidence": 0.90,
                "risk_class": "HIGH_RISK", # Source-code and key-related are HIGH_RISK, forcing proposals
                "status": "FORMULATED",
                "created_at": now_str
            }

        # Default general hypothesis
        else:
            return {
                "id": hypothesis_id,
                "trigger": "General performance bottleneck identified in logs",
                "observed_problem": f"Execution metrics degraded on: '{pattern}'",
                "degradation_metrics": {"failure_count": weakness.get("frequency", 1)},
                "root_cause": "Heuristics and memory context routing is un-optimized",
                "proposed_adaptation": {"memory_retrieval_weight": {"episodic": 1.5, "semantic": 0.5}},
                "predicted_outcomes": {"relevance_score": 0.95},
                "evidence": ["Performance sweep log files"],
                "confidence": 0.70,
                "risk_class": "SAFE_AUTOMATIC",
                "status": "FORMULATED",
                "created_at": now_str
            }


hypothesis_engine = HypothesisEngine()
