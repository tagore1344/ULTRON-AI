from urllib.parse import quote

from .browser_manager import BrowserManager


class BrowserSearch:

    def __init__(self):

        self.browser = BrowserManager()

    def google(self, query):

        url = f"https://www.google.com/search?q={quote(query)}"

        self.browser.open(url)

        return True

    def youtube(self, query):

        url = f"https://www.youtube.com/results?search_query={quote(query)}"

        self.browser.open(url)

        return True

    def github(self, query):

        url = f"https://github.com/search?q={quote(query)}"

        self.browser.open(url)

        return True

    def wikipedia(self, query):

        url = f"https://en.wikipedia.org/wiki/Special:Search?search={quote(query)}"

        self.browser.open(url)

        return True