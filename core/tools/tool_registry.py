# core/tools/tool_registry.py — Tool execution registry
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

        if intent == "system.update_check" or intent == "system.update_status":
            try:
                from core.update.update_manager import update_manager
                return str(update_manager.get_status())
            except Exception as e:
                return f"Update service failed: {e}"

        if intent == "app.open":
            target_lower = target.lower().strip()

            # Safe bounded alias mapping for voice transcription typos
            if target_lower == "chroome":
                target_lower = "chrome"
            elif target_lower == "google chrome":
                target_lower = "chrome"

            # 1. Explicit website/web-shortcut mapping (bypasses native executable launchers)
            if target_lower in ("youtube", "instagram", "facebook", "twitter", "google", "github"):
                if self.system:
                    if target_lower == "youtube":
                        return self.system.open_website("www.youtube.com")
                    elif target_lower == "instagram":
                        return self.system.open_website("www.instagram.com")
                    else:
                        return self.system.open_website(f"www.{target_lower}.com")
                return "System control unavailable."

            # 2. Use AppController to launch native desktop applications
            if self.apps:
                success = self.apps.open_app(target_lower)
                if success:
                    return f"Successfully opened {target_lower}."
                else:
                    # Graceful browser fallback for WhatsApp if not installed locally
                    if target_lower == "whatsapp" and self.system:
                        self.system.open_website("web.whatsapp.com")
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

        return f"Unknown tool intent: {intent}"
