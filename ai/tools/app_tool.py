from .base_tool import BaseTool
from app_controller import AppController


class AppTool(BaseTool):

    def __init__(self, speech):

        super().__init__("app_launcher")

        self.app = AppController(speech)

    def execute(self, task):

        action = task.parameters.get("action", "open")

        application = task.parameters.get("application")

        if action == "open":

            return self.app.open_app(application)

        elif action == "close":

            return self.app.close_app(application)

        elif action == "switch":

            return self.app.switch_to_app(application)

        else:

            return f"Unknown action: {action}"