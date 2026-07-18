from urllib.parse import quote

from .base_skill import BaseSkill


class SearchSkill(BaseSkill):

    def google(self, query):

        url = "https://www.google.com/search?q=" + quote(query)

        return self.browser.open(url)

    def youtube(self, query):

        url = "https://www.youtube.com/results?search_query=" + quote(query)

        return self.browser.open(url)

    def github(self, query):

        url = "https://github.com/search?q=" + quote(query)

        return self.browser.open(url)

    def wikipedia(self, query):

        url = (
            "https://en.wikipedia.org/wiki/Special:Search?search="
            + quote(query)
        )

        return self.browser.open(url)