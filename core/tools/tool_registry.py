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


class ToolRegistry:
    """Executes tool intents detected by the IntentRouter."""

    def __init__(self):
        self.speech = None
        if AdvancedSpeechEngine is not None:
            try:
                self.speech = AdvancedSpeechEngine()
            except Exception:
                self.speech = None

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

        if intent == "app.open":
            if self.system:
                return self.system.open_website(target)
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