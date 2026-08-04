# services/automation_service.py — Automation service layer
try:
    from system_controller import SystemController
except Exception:
    SystemController = None

try:
    from speech_engine_advanced import AdvancedSpeechEngine
except Exception:
    AdvancedSpeechEngine = None


class AutomationService:
    """Service layer for system automation — wraps the system controller."""

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
            except Exception as e:
                print(f"[AUTOMATION SERVICE] System init failed: {e}")

    def volume_up(self, amount=10):
        if self.system:
            return self.system.volume_up(amount)
        return "Automation service unavailable."

    def volume_down(self, amount=10):
        if self.system:
            return self.system.volume_down(amount)
        return "Automation service unavailable."

    def set_volume(self, level):
        if self.system:
            return self.system.set_volume(level)
        return "Automation service unavailable."

    def brightness_up(self):
        if self.system:
            return self.system.brightness_up()
        return "Automation service unavailable."

    def brightness_down(self):
        if self.system:
            return self.system.brightness_down()
        return "Automation service unavailable."

    def set_brightness(self, level):
        if self.system:
            return self.system.set_brightness(level)
        return "Automation service unavailable."

    def get_time(self):
        if self.system:
            return self.system.get_time()
        return "Automation service unavailable."

    def get_date(self):
        if self.system:
            return self.system.get_date()
        return "Automation service unavailable."

    def get_battery(self):
        if self.system:
            return self.system.get_battery()
        return "Automation service unavailable."

    def get_system_info(self):
        if self.system:
            return self.system.get_system_info()
        return "Automation service unavailable."

    def google_search(self, query):
        if self.system:
            return self.system.google_search(query)
        return "Automation service unavailable."

    def open_website(self, url):
        if self.system:
            return self.system.open_website(url)
        return "Automation service unavailable."

    def youtube_search(self, query):
        if self.system:
            return self.system.youtube_search(query)
        return "Automation service unavailable."