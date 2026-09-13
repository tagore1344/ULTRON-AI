# system_tool.py

from core.tools.system_controller import SystemController


class SystemTool:

    def __init__(self):

        self.controller = SystemController(None)

    def volume_up(self, _=None):

        self.controller.volume_up()

        return "Volume increased"

    def volume_down(self, _=None):

        self.controller.volume_down()

        return "Volume decreased"