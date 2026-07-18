from .base_tool import BaseTool
import webbrowser
import urllib.parse


class WebSearchTool(BaseTool):

    def __init__(self):

        super().__init__("web_search")

    def execute(self, task):

        query = task.parameters.get("query", "")

        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote(query)
        )

        webbrowser.open(url)

        return True