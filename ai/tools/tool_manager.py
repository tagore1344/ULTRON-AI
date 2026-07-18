from .tool_registry import ToolRegistry

from .ai_tool import AITool
from .app_tool import AppTool
from .system_tool import SystemTool
from .web_search_tool import WebSearchTool
from .browser_tool import BrowserTool
from .browser_automation_tool import BrowserAutomationTool


class ToolManager:

    def __init__(self, speech):

        # Create registry FIRST
        self.registry = ToolRegistry()

        # Register all tools
        self.registry.register(AITool())
        self.registry.register(AppTool(speech))
        self.registry.register(SystemTool(speech))
        self.registry.register(WebSearchTool())
        self.registry.register(BrowserTool())
        self.registry.register(BrowserAutomationTool())

    def get_tool(self, name):

        return self.registry.get(name)

    def available_tools(self):

        return self.registry.list_tools()