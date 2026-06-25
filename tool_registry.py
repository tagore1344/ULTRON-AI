# tool_registry.py

class ToolRegistry:

    def __init__(self, jarvis):

        self.jarvis = jarvis

        # ─────────────────────────
        # TOOLS
        # ─────────────────────────
        self.tools = {

            "app.open":
                self.open_app,

            "app.close":
                self.close_app,

            "web.search":
                self.google_search,

            "youtube.search":
                self.youtube_search,

            "system.volume_up":
                self.volume_up,

            "system.volume_down":
                self.volume_down,

            "system.screenshot":
                self.screenshot,

            "system.time":
                self.time,

            "system.date":
                self.date
        }

    # ─────────────────────────────────────
    # EXECUTE
    # ─────────────────────────────────────
    def execute(self, intent, target):

        if intent not in self.tools:

            return False

        tool = self.tools[intent]

        tool(target)

        return True

    # ─────────────────────────────────────
    # TOOLS
    # ─────────────────────────────────────
    def open_app(self, target):

        self.jarvis.apps.open_app(target)

    def close_app(self, target):

        self.jarvis.apps.close_app(target)

    def google_search(self, target):

        self.jarvis.system.google_search(target)

    def youtube_search(self, target):

        self.jarvis.system.youtube_search(target)

    def volume_up(self, target):

        self.jarvis.system.volume_up()

    def volume_down(self, target):

        self.jarvis.system.volume_down()

    def screenshot(self, target):

        self.jarvis.apps.take_screenshot()

    def time(self, target):

        self.jarvis.system.get_time()

    def date(self, target):

        self.jarvis.system.get_date()