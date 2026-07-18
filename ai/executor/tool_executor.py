from ai.tools.tool_manager import ToolManager


class ToolExecutor:

    def __init__(self, speech):

        self.tool_manager = ToolManager(speech)

    def execute(self, task):

        tool = self.tool_manager.get_tool(task.tool)

        if tool is None:
            return f"Unknown Tool: {task.tool}"

        try:
            return tool.execute(task)

        except Exception as e:
            return f"Tool Error ({task.tool}): {e}"