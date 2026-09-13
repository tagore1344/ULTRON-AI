# web_tool.py

import webbrowser
import urllib.parse


class WebTool:

    def search(self, query):

        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote(query)
        )

        webbrowser.open(url)

        return f"Searching for {query}"