# core/neural/neural_schema.py
import datetime
import re
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any

# Secure regex-based credentials redactor
def sanitize_metadata(props: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures no raw API keys, bearer tokens, or sensitive credentials leak into node attributes."""
    sanitized = {}
    for k, v in props.items():
        if isinstance(v, str):
            # Redact Bearer tokens
            v = re.sub(r'(?i)bearer\s+[a-zA-Z0-9_\-\.]+', 'Bearer <REDACTED_TOKEN>', v)
            # Redact generic credentials and API keys
            v = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-<REDACTED_OPENAI_KEY>', v)
            v = re.sub(r'AIzaSy[a-zA-Z0-9_\-]{33}', 'AIzaSy<REDACTED_GOOGLE_KEY>', v)
            v = re.sub(r'(?i)(password|passphrase|secret|key|token|auth_token|access_token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\@]+["\']?', r'\1=<REDACTED>', v)
        sanitized[k] = v
    return sanitized


class NeuralNodeModel(BaseModel):
    node_id: str = Field(..., description="Unique global node identifier.")
    node_type: str = Field(..., description="ENTITY, CONCEPT, EVENT, or STATE.")
    label: str = Field(..., description="Human-readable descriptive label.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata key-values.")
    belief_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Subjective probability B.")
    operational_state: str = Field("UNVERIFIED", description="KNOWN, UNVERIFIED, FAILED, or BLOCKED.")
    last_updated: str = Field(..., description="ISO 8601 UTC timestamp.")

    @field_validator("properties")
    @classmethod
    def validate_and_sanitize_properties(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that properties are safe from malicious code payloads and redacts secrets."""
        # 1. Reject Python payloads to enforce security immutability
        props_str = str(v).lower()
        forbidden_signatures = ["import ", "eval(", "exec(", "subprocess", "os.system"]
        for signature in forbidden_signatures:
            if signature in props_str:
                raise ValueError(f"Malicious payload blocked: '{signature}' is prohibited.")
        # 2. Sanitize any secrets
        return sanitize_metadata(v)

    def evaluate_operational_state(self) -> str:
        """
        Policy-driven state classification engine.
        Decouples raw Bayesian confidence values from operational state assignments.
        """
        # Exclude blocked states
        if self.operational_state == "BLOCKED":
            return "BLOCKED"

        b = self.belief_confidence
        if b >= 0.85:
            return "KNOWN"
        elif 0.35 <= b < 0.85:
            return "UNVERIFIED"
        else:
            return "FAILED"


class NeuralEdgeModel(BaseModel):
    edge_id: str = Field(..., description="Unique edge identifier.")
    source_id: str = Field(..., description="Source node ID.")
    target_id: str = Field(..., description="Target node ID.")
    relationship_type: str = Field(..., description="HAS_STATE, CAUSES, DEPENDS_ON, or ASSOCIATED_WITH.")
    link_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in connection.")
    causal_influence_delta: float = Field(default=0.0, ge=-1.0, le=1.0, description="Directional impact multiplier.")
