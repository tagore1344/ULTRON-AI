from .tool_registry import ToolRegistry

from .app_tool import AppTool
from .system_tool import SystemTool
from .web_search_tool import WebSearchTool
from .browser_tool import BrowserTool


class ToolManager:

    def __init__(self, speech):

        self.registry = ToolRegistry()

        self.registry.register(AppTool(speech))
        self.registry.register(SystemTool(speech))
        self.registry.register(WebSearchTool())
        self.registry.register(BrowserTool())

    def get_tool(self, name):

        return self.registry.get(name)

    def available_tools(self):

        return self.registry.list_tools()