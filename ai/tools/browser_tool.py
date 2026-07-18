from .base_tool import BaseTool
import webbrowser
import urllib.parse


class BrowserTool(BaseTool):

    def __init__(self):

        super().__init__("browser")

        self.websites = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "github": "https://github.com",
            "linkedin": "https://www.linkedin.com",
            "gmail": "https://mail.google.com",
            "chatgpt": "https://chatgpt.com",
            "claude": "https://claude.ai",
            "deepseek": "https://chat.deepseek.com",
            "stackoverflow": "https://stackoverflow.com",
            "wikipedia": "https://www.wikipedia.org",
            "reddit": "https://www.reddit.com",
            "x": "https://x.com",
            "twitter": "https://x.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "amazon": "https://www.amazon.in",
            "netflix": "https://www.netflix.com",
            "spotify": "https://open.spotify.com",
            "leetcode": "https://leetcode.com",
            "hackerrank": "https://www.hackerrank.com",
            "codeforces": "https://codeforces.com"
        }

    def execute(self, task):

        website = task.parameters.get("website", "").lower()
        url = task.parameters.get("url")
        query = task.parameters.get("query")

        if url:
            webbrowser.open(url)
            return True

        if website:

            if website not in self.websites:
                return f"Unknown website: {website}"

            webbrowser.open(self.websites[website])
            return True

        if query:
            search_url = (
                "https://www.google.com/search?q="
                + urllib.parse.quote(query)
            )

            webbrowser.open(search_url)
            return True

        return "Nothing to open."