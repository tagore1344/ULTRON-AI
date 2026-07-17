from app_controller import AppController
from system_controller import SystemController


class ToolExecutor:

    def __init__(self):

        self.app = AppController()

        self.system = SystemController()

    def execute(self, task):

        tool = task.tool

        if tool == "app_launcher":

            application = task.parameters.get(
                "application"
            )

            return self.app.open_application(
                application
            )

        elif tool == "system":

            action = task.parameters.get(
                "action"
            )

            return self.system.execute(
                action
            )

        elif tool == "ai":

            return "Forward task to AI"

        else:

            return f"Unknown Tool: {tool}"