# tool_registry.py — TAG runtime bridge

class ToolRegistry:
    """Synchronous legacy tool registry used by assistant_with_brain.py."""

    def __init__(self, jarvis):
        self.jarvis = jarvis
        self.tools = {
            "app.open": self.open_app,
            "app.close": self.close_app,
            "web.search": self.google_search,
            "youtube.search": self.youtube_search,
            "system.volume_up": self.volume_up,
            "system.volume_down": self.volume_down,
            "system.screenshot": self.screenshot,
            "system.time": self.time,
            "system.date": self.date,
        }

    def execute(self, intent, target):
        tool = self.tools.get(intent)
        if tool is None:
            return False
        try:
            tool(target)
            return True
        except Exception as exc:
            print(f"[TOOL ERROR] {intent}: {exc}")
            return False

    def open_app(self, target):
        return self.jarvis.apps.open_app(target)

    def close_app(self, target):
        return self.jarvis.apps.close_app(target)

    def google_search(self, target):
        return self.jarvis.system.google_search(target)

    def youtube_search(self, target):
        return self.jarvis.system.youtube_search(target)

    def volume_up(self, target):
        return self.jarvis.system.volume_up()

    def volume_down(self, target):
        return self.jarvis.system.volume_down()

    def screenshot(self, target):
        return self.jarvis.apps.take_screenshot()

    def time(self, target):
        return self.jarvis.system.get_time()

    def date(self, target):
        return self.jarvis.system.get_date()
