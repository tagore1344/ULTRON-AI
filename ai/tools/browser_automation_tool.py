from .base_tool import BaseTool
from ai.browser.browser_manager import BrowserManager
from ai.browser.skills.navigation_skill import NavigationSkill
from ai.browser.skills.interaction_skill import InteractionSkill
from ai.browser.skills.search_skill import SearchSkill


class BrowserAutomationTool(BaseTool):

    def __init__(self):

        super().__init__("browser_automation")

        self.browser = BrowserManager()

        self.navigation = NavigationSkill(self.browser)

        self.interaction = InteractionSkill(self.browser)

        self.search = SearchSkill(self.browser)

    def execute(self, task):

        action = task.parameters.get("action")

        if action == "open_url":

            return self.navigation.open(
                task.parameters["url"]
            )

        elif action == "google_search":

            return self.search.google(
                task.parameters["query"]
            )

        elif action == "youtube_search":

            return self.search.youtube(
                task.parameters["query"]
            )

        elif action == "github_search":

            return self.search.github(
                task.parameters["query"]
            )

        elif action == "wikipedia_search":

            return self.search.wikipedia(
                task.parameters["query"]
            )

        elif action == "click":

            return self.interaction.click(
                task.parameters["selector"]
            )

        elif action == "type":

            return self.interaction.type(
                task.parameters["selector"],
                task.parameters["text"]
            )

        elif action == "press":

            return self.interaction.press(
                task.parameters["selector"],
                task.parameters["key"]
            )

        elif action == "wait":

            return self.interaction.wait(
                task.parameters["seconds"]
            )

        elif action == "screenshot":

            return self.interaction.screenshot(
                task.parameters.get(
                    "filename",
                    "browser.png"
                )
            )

        else:

            return f"Unknown browser action: {action}"