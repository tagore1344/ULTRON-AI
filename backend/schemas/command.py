# backend/schemas/command.py
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class SecurityLevel(str, Enum):
    """Canonical permission classifications for all system operations."""

    SAFE = "SAFE"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class CommandRequest(BaseModel):
    """Pydantic schema validating incoming client command execution payloads."""

    command: str = Field(..., description="The name of the target command to execute.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary parameters passed to the target command."
    )

    @field_validator("command")
    @classmethod
    def block_unauthorized_commands(cls, v: str) -> str:
        command_clean = v.lower().strip()

        # Explicit blocklist of dangerous raw interpreters
        # Check for exact matches to avoid partial matching errors on short strings like "sh" in "shutdown"
        forbidden_interpreters = {
            "python", "powershell", "sh", "bash", "cmd", "cmd.exe", "subprocess", "eval", "exec"
        }

        if command_clean in forbidden_interpreters:
            raise ValueError(f"Direct interpreter execution '{v}' is strictly prohibited.")

        # Check dangerous sub-phrases
        dangerous_substrings = ["os.system", "subprocess.popen", "subprocess.run"]
        for substring in dangerous_substrings:
            if substring in command_clean:
                raise ValueError(f"Command execution of raw shell phrase '{v}' is strictly prohibited.")

        return command_clean


class CommandResponse(BaseModel):
    """Pydantic schema validating system command responses."""

    success: bool = Field(..., description="Whether the command succeeded or was rejected.")
    command_id: str = Field(..., description="Unique random transaction tracking identifier.")
    status: str = Field(..., description="Execution status: completed, pending, or rejected.")
    result: Optional[Dict[str, Any]] = Field(None, description="The execution result data payload.")
