# core/tools/tool_registry.py — Tool execution registry
import asyncio
import logging

try:
    from system_controller import SystemController
except Exception:
    SystemController = None

try:
    from screen_vision import ScreenVision
except Exception:
    ScreenVision = None

try:
    from speech_engine_advanced import AdvancedSpeechEngine
except Exception:
    AdvancedSpeechEngine = None

try:
    from app_controller import AppController
except Exception:
    AppController = None

logger = logging.getLogger("ultron-api")


class ToolRegistry:
    """Executes tool intents detected by the IntentRouter."""

    def __init__(self):
        self.speech = None
        if AdvancedSpeechEngine is not None:
            try:
                self.speech = AdvancedSpeechEngine()
            except Exception:
                self.speech = None

        self.apps = None
        if AppController is not None:
            try:
                self.apps = AppController(self.speech)
            except Exception:
                self.apps = None

        self.system = None
        if SystemController is not None:
            try:
                self.system = SystemController(self.speech)
            except Exception:
                self.system = None

        self.vision = None
        if ScreenVision is not None:
            try:
                self.vision = ScreenVision()
            except Exception:
                self.vision = None

    async def execute(self, intent_data):
        """Execute a tool based on the intent data dict."""
        intent = intent_data.get("intent", "chat")
        target = intent_data.get("target", "")

        if intent == "composite":
            results = []
            for action in intent_data.get("actions", []):
                res = await self.execute(action)
                results.append(str(res))
            return "\n".join(results)

        if intent == "app.send_message":
            recipient = intent_data.get("recipient", "")
            message = intent_data.get("message", "")
            app_name = intent_data.get("app", "whatsapp")

            print(f"[CONFIRMATION REQUIRED] Send {app_name} message to '{recipient}'?")
            print(f"Message text: '{message}'")
            return "WhatsApp message prepared for confirmation, but sending is not yet supported."

        if intent == "system.time":
            if self.system:
                return self.system.get_time()
            return "Time tool unavailable."

        if intent == "system.date":
            if self.system:
                return self.system.get_date()
            return "Date tool unavailable."

        if intent == "system.volume_up":
            if self.system:
                return self.system.volume_up()
            return "Volume tool unavailable."

        if intent == "system.volume_down":
            if self.system:
                return self.system.volume_down()
            return "Volume tool unavailable."

        if intent == "system.brightness_up":
            if self.system:
                return self.system.brightness_up()
            return "Brightness tool unavailable."

        if intent == "system.brightness_down":
            if self.system:
                return self.system.brightness_down()
            return "Brightness tool unavailable."

        if intent == "system.screenshot":
            if self.vision:
                return self.vision.capture_screen()
            return "Screenshot tool unavailable."

        if intent == "system.screen_read":
            if self.vision:
                return self.vision.analyze_screen()
            return "Screen reading tool unavailable."

        if intent == "system.battery":
            if self.system:
                return self.system.get_battery()
            return "Battery tool unavailable."

        if intent == "system.info":
            if self.system:
                return self.system.get_system_info()
            return "System info tool unavailable."

        if intent == "agent.get_status":
            try:
                from core.agent.agent_runtime import agent_runtime
                return str(agent_runtime.get_status())
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.get_opinion":
            try:
                from core.agent.agent_runtime import agent_runtime
                opinion = agent_runtime.get_opinion()
                if opinion:
                    return str(opinion.to_dict())
                return "No opinion has been formulated yet."
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.get_self_evaluation":
            try:
                from core.agent.agent_runtime import agent_runtime
                evaluation = agent_runtime.get_self_evaluation()
                if evaluation:
                    return str(evaluation)
                return "No self-evaluation has been recorded yet."
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.get_self_model":
            try:
                from core.context.self_model import self_model
                return str(self_model.get_summary())
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.get_world_model":
            try:
                from core.context.world_model import world_model
                return str(world_model.get_summary())
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.get_active_goals":
            try:
                from core.context.long_term_goals import goal_manager_9b
                return str(goal_manager_9b.get_active_goals_with_subgoals())
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.clear_memory":
            try:
                from core.context.memory_manager import memory_manager
                memory_manager.clear_all_context_memory()
                return "All contextual memory pools successfully cleared."
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.cancel_goal":
            try:
                from core.agent.goal_manager import goal_manager
                return str(goal_manager.cancel_goal())
            except Exception as e:
                return f"Agent service failure: {e}"

        if intent == "agent.set_autonomy":
            try:
                from core.agent.policy_engine import policy_engine
                level = int(target) if str(target).isdigit() else 3
                return str(policy_engine.set_autonomy(level))
            except Exception as e:
                return f"Agent service failure: {e}"
        if intent == "system.update_check" or intent == "system.update_status":
            try:
                from core.update.update_manager import update_manager
                return str(update_manager.get_status())
            except Exception as e:
                return f"Update service failed: {e}"

        if intent == "app.open":
            target_lower = target.lower().strip()

            # 0. Config-backed voice alias mapping (populated by approved Phase 9E proposals)
            try:
                from core.config import load_config
                voice_aliases = load_config().get("voice_aliases") or {}
                if isinstance(voice_aliases, dict) and target_lower in voice_aliases:
                    mapped = str(voice_aliases[target_lower]).lower().strip()
                    if mapped:
                        logger.info("Voice alias applied: '%s' -> '%s'", target_lower, mapped)
                        target_lower = mapped
            except Exception as e:
                logger.debug("Voice alias lookup bypassed: %s", e)

            # Safe bounded alias mapping for voice transcription typos
            if target_lower == "chroome":
                target_lower = "chrome"
            elif target_lower == "google chrome":
                target_lower = "chrome"

            # 1. Explicit website/web-shortcut mapping (bypasses native executable launchers)
            if target_lower in ("youtube", "instagram", "facebook", "twitter", "google", "github"):
                if self.system:
                    if target_lower == "youtube":
                        await asyncio.to_thread(self.system.open_website, "www.youtube.com")
                    elif target_lower == "instagram":
                        await asyncio.to_thread(self.system.open_website, "www.instagram.com")
                    else:
                        await asyncio.to_thread(self.system.open_website, f"www.{target_lower}.com")
                    return f"Opened {target_lower} in your browser."
                return "System control unavailable."

            # 2. Use AppController to launch native desktop applications (offloaded to a thread)
            if self.apps:
                success = await asyncio.to_thread(self.apps.open_app, target_lower)
                if success:
                    return f"Successfully opened {target_lower}."
                else:
                    # Graceful browser fallback for WhatsApp if not installed locally
                    if target_lower == "whatsapp" and self.system:
                        await asyncio.to_thread(self.system.open_website, "web.whatsapp.com")
                        return "Local WhatsApp is not installed. Opened WhatsApp Web in your browser instead."
                    return f"Application {target_lower} not found or failed to open."
            return "App launcher unavailable."

        if intent == "web.search":
            if self.system:
                return self.system.google_search(target)
            return "Web search unavailable."

        if intent == "youtube.search":
            if self.system:
                return self.system.youtube_search(target)
            return "YouTube search unavailable."

        # ==============================================================================
        # POWER COMMANDS (HIGH_RISK — enforced upstream by command_service confirmation gate)
        # Async variants offload blocking OS calls off the event loop.
        # ==============================================================================
        if intent == "system.shutdown":
            if not self.system:
                return "System control unavailable."
            fn = getattr(self.system, "ashutdown", None) or self.system.shutdown
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                await asyncio.to_thread(fn)
            return "Shutdown initiated."

        if intent == "system.restart":
            if not self.system:
                return "System control unavailable."
            fn = getattr(self.system, "arestart", None) or self.system.restart
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                await asyncio.to_thread(fn)
            return "Restart initiated."

        if intent == "system.sleep":
            if not self.system:
                return "System control unavailable."
            fn = getattr(self.system, "asleep", None) or self.system.sleep
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                await asyncio.to_thread(fn)
            return "Sleep initiated."

        if intent == "system.lock_screen":
            if not self.system:
                return "System control unavailable."
            fn = getattr(self.system, "alock_screen", None) or self.system.lock_screen
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                await asyncio.to_thread(fn)
            return "Screen locked."

        if intent == "system.cancel_shutdown":
            if not self.system:
                return "System control unavailable."
            fn = getattr(self.system, "acancel_shutdown", None) or self.system.cancel_shutdown
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                await asyncio.to_thread(fn)
            return "Shutdown cancelled."

        return f"Unknown tool intent: {intent}"
