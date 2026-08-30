# core/update/update_policy.py
from enum import Enum


class UpdateRiskClass(str, Enum):
    SAFE_AUTOMATIC = "SAFE_AUTOMATIC"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class UpdatePolicy:
    """Enforces fine-grained risk-classification policies and permission checks for self-updates."""

    @staticmethod
    def classify_update(modified_files: list) -> UpdateRiskClass:
        """Analyze changed files list and map them to their corresponding risk categories."""
        # 1. High-risk critical security subsystem indicators
        high_risk_triggers = [
            "backend/security/", "backend/schemas/command.py",
            "backend/schemas/event.py", "microphone_broker.py",
            "core/update/", "bootstrap_launcher.py"
        ]
        for f in modified_files:
            for trigger in high_risk_triggers:
                if trigger in f:
                    return UpdateRiskClass.HIGH_RISK

        # 2. Review-required standard source/dependencies indicators
        review_required_triggers = [
            "backend/api/", "app_controller.py", "system_controller.py",
            "core/tools/", "speech_engine_advanced.py", "requirements_backend.txt"
        ]
        for f in modified_files:
            for trigger in review_required_triggers:
                if trigger in f:
                    return UpdateRiskClass.REVIEW_REQUIRED

        # 3. Safe, automatic candidates (AI prompts, documentation, configs)
        return UpdateRiskClass.SAFE_AUTOMATIC


update_policy = UpdatePolicy()
