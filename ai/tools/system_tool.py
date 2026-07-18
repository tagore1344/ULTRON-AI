from .base_tool import BaseTool
from system_controller import SystemController


class SystemTool(BaseTool):

    def __init__(self, speech):

        super().__init__("system")

        self.system = SystemController(speech)

    def execute(self, task):

        action = task.parameters.get("action")

        return self.system.execute(action)