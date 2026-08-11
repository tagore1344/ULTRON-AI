# backend/services/command_service.py
import logging
import uuid
import datetime
from typing import Dict, Any, Tuple

from backend.schemas.command import SecurityLevel
from core.tools.tool_registry import ToolRegistry

logger = logging.getLogger("ultron-api")


class CommandService:
    """Manages secure, audited command execution pipelines connecting to canonical tools."""

    def __init__(self):
        try:
            self.registry = ToolRegistry()
            logger.info("CommandService connected to canonical ToolRegistry successfully.")
        except Exception as e:
            logger.critical("Failed to instantiate canonical ToolRegistry: %s", e)
            self.registry = None

        # Expose strictly allowed commands and map them to standard categories
        self.allowlist_categories: Dict[str, SecurityLevel] = {
            # --- SAFE COMMANDS ---
            "get_system_status": SecurityLevel.SAFE,
            "get_time": SecurityLevel.SAFE,
            "get_date": SecurityLevel.SAFE,
            "get_battery_status": SecurityLevel.SAFE,
            "get_cpu_status": SecurityLevel.SAFE,
            "get_memory_status": SecurityLevel.SAFE,

            # --- CONFIRMATION REQUIRED COMMANDS ---
            "launch_application": SecurityLevel.CONFIRMATION_REQUIRED,
            "open_website": SecurityLevel.CONFIRMATION_REQUIRED,
            "volume_up": SecurityLevel.CONFIRMATION_REQUIRED,
            "volume_down": SecurityLevel.CONFIRMATION_REQUIRED,
            "screenshot": SecurityLevel.CONFIRMATION_REQUIRED,

            # --- HIGH RISK COMMANDS ---
            "shutdown": SecurityLevel.HIGH_RISK,
            "restart": SecurityLevel.HIGH_RISK,
            "delete_files": SecurityLevel.HIGH_RISK,
            "lock_screen": SecurityLevel.HIGH_RISK,
        }

    def _map_to_intent_data(self, command: str, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """Translate API command inputs into canonical core intent routing payloads."""
        cmd = command.lower().strip()

        if cmd == "get_time":
            return "system.time", ""
        elif cmd == "get_date":
            return "system.date", ""
        elif cmd in ("get_battery_status", "get_system_status"):
            return "system.battery", ""
        elif cmd in ("get_cpu_status", "get_memory_status"):
            return "system.info", ""
        elif cmd == "volume_up":
            return "system.volume_up", ""
        elif cmd == "volume_down":
            return "system.volume_down", ""
        elif cmd == "screenshot":
            return "system.screenshot", ""
        elif cmd == "launch_application":
            target = parameters.get("application", "")
            return "app.open", target
        elif cmd == "open_website":
            target = parameters.get("url", "")
            return "app.open", target

        return "chat", ""

    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrates the formal validation, classification, and execution lifecycle of commands."""
        command_id = f"cmd_{uuid.uuid4().hex[:12]}"
        logger.info("COMMAND_RECEIVED %s - Target: %s", command_id, command)

        cmd = command.lower().strip()

        # 1. Validation & Allowlist Check
        if cmd not in self.allowlist_categories:
            logger.warning("COMMAND_REJECTED %s - Unknown command string", command_id)
            return {
                "success": False,
                "command_id": command_id,
                "status": "rejected",
                "error": {
                    "code": "COMMAND_NOT_ALLOWED",
                    "message": f"Command '{command}' is not available through the API."
                }
            }

        logger.info("COMMAND_VALIDATED %s", command_id)

        # 2. Classification Check
        security_level = self.allowlist_categories[cmd]
        logger.info("COMMAND_CLASSIFIED %s - Security Level: %s", command_id, security_level.value)

        # 3. High-Risk Guardrails (Phase 2 limitation)
        if security_level == SecurityLevel.HIGH_RISK:
            logger.warning("COMMAND_REJECTED %s - High-risk execution blocked in Phase 2 gateway", command_id)
            return {
                "success": False,
                "command_id": command_id,
                "status": "rejected",
                "error": {
                    "code": "HIGH_RISK_COMMAND_REQUIRES_AUTHORIZATION",
                    "message": "This command is classified as HIGH_RISK and requires authenticated device confirmation."
                }
            }

        # 4. Confirmation required warnings
        if security_level == SecurityLevel.CONFIRMATION_REQUIRED:
            # During development, we let it pass but flag it
            logger.info("COMMAND_AUTHORIZED %s - CONFIRMATION_REQUIRED execution bypassed in local development mode", command_id)
        else:
            logger.info("COMMAND_AUTHORIZED %s", command_id)

        if self.registry is None:
            logger.error("COMMAND_REJECTED %s - Canonical tool registry is unavailable", command_id)
            return {
                "success": False,
                "command_id": command_id,
                "status": "rejected",
                "error": {
                    "code": "TOOL_REGISTRY_OFFLINE",
                    "message": "Canonical ULTRON Tool Registry is offline."
                }
            }

        # 5. Intent Translation and Execution
        intent, target = self._map_to_intent_data(cmd, parameters)
        logger.info("COMMAND_STARTED %s - Routing intent: %s (target: %s)", command_id, intent, target)

        try:
            # Invoke the canonical tool registry execution pipeline asynchronously
            result = await self.registry.execute({
                "intent": intent,
                "target": target
            })
            
            logger.info("COMMAND_COMPLETED %s", command_id)
            return {
                "success": True,
                "command_id": command_id,
                "status": "completed",
                "result": {
                    "message": f"Command '{command}' completed successfully.",
                    "response": result
                }
            }
        except Exception as e:
            logger.error("COMMAND_FAILED %s - Execution error: %s", command_id, e, exc_info=True)
            return {
                "success": False,
                "command_id": command_id,
                "status": "failed",
                "error": {
                    "code": "EXECUTION_ANOMALY",
                    "message": f"Tool execution failed: {str(e)}"
                }
            }


# Singleton instance of command dispatch coordinator
command_service = CommandService()
