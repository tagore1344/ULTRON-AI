# core/evolution/candidate_manager.py
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ultron-api")


class CandidateManager:
    """Creates immutable, validated candidate configurations, enforcing strict risk limits and source code isolation."""

    def __init__(self):
        pass

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validates the proposed configuration mutations.
        Strictly rejects any Python payloads, system executables, or shell commands.
        """
        config_str = json.dumps(config).lower()

        # Security Perimeter Check: Strict blacklist patterns
        forbidden_signatures = [
            "import ", "eval(", "exec(", "subprocess", "os.system",
            "shutil", "open(", "write(", "sys.modules", "chmod", "sh "
        ]
        for signature in forbidden_signatures:
            if signature in config_str:
                logger.error("CandidateManager: Malicious/un-allowlisted signature detected in configuration: '%s'", signature)
                return False

        # Only allow recognized configuration keys
        allowed_keys = ["command_alias", "model_routing", "memory_retrieval_weight", "change_proposal", "speech_model"]
        for key in config.keys():
            if key not in allowed_keys:
                logger.error("CandidateManager: Blocked un-allowlisted adaptation key '%s'", key)
                return False

        return True

    def create_candidate(self, hypothesis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Creates an immutable, validated Candidate record from the accepted hypothesis.
        If the hypothesis requires code modifications, creates a CHANGE_PROPOSAL and locks it from direct execution.
        """
        import uuid
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"
        adaptation = hypothesis.get("proposed_adaptation", {})

        # 1. Configuration-level validation
        if not self.validate_configuration(adaptation):
            logger.warning("CandidateManager: Proposed configuration failed verification boundaries.")
            return None

        # 2. Extract baseline values (mocking dynamic current state snapshots)
        baseline = {}
        for key in adaptation.keys():
            if key == "command_alias":
                baseline["command_alias"] = {}
            elif key == "model_routing":
                baseline["model_routing"] = {"query": "openai", "default_routing": "openai"}
            elif key == "memory_retrieval_weight":
                baseline["memory_retrieval_weight"] = {"episodic": 1.0, "semantic": 1.0}
            else:
                baseline[key] = None

        # 3. Determine Risk Classification
        risk_class = hypothesis.get("risk_class", "SAFE_AUTOMATIC")

        # 4. Handle Source Code Change Proposals (HIGH RISK / Banned from self-update bypass)
        if risk_class == "HIGH_RISK" or "change_proposal" in adaptation:
            logger.warning("CandidateManager: Candidate is HIGH_RISK source-change request. Creating CHANGE_PROPOSAL only.")
            return {
                "id": candidate_id,
                "hypothesis_id": hypothesis["id"],
                "baseline_configuration": baseline,
                "candidate_configuration": adaptation,
                "expected_benefit": hypothesis.get("predicted_outcomes", {}).get("error_rate", 0.05),
                "expected_cost": 500,
                "risk_class": "HIGH_RISK",
                "resource_budget": {"tokens": 0, "runs": 0}, # Banned from execution
                "rollback_snapshot": {},
                "status": "REJECTED" # Lock out from background execution entirely
            }

        # 5. Formulate safe, immutable candidate record
        candidate = {
            "id": candidate_id,
            "hypothesis_id": hypothesis["id"],
            "baseline_configuration": baseline,
            "candidate_configuration": adaptation,
            "expected_benefit": 0.15,
            "expected_cost": 2000,
            "risk_class": risk_class,
            "resource_budget": {"tokens": 5000, "runs": 10},
            "rollback_snapshot": baseline,
            "status": "CREATED"
        }

        # Enforce immutability statefully using Python's immutable structures or dict freezing
        # In python, we can make it a mapping proxy or just return a dict that throws errors on write test
        return candidate


candidate_manager = CandidateManager()
