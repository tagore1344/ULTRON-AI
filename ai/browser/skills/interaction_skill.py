from .base_skill import BaseSkill


class InteractionSkill(BaseSkill):

    def click(self, selector):

        return self.browser.click(selector)

    def type(self, selector, text):

        return self.browser.type(selector, text)

    def press(self, selector, key):

        return self.browser.press(selector, key)

    def wait(self, seconds):

        return self.browser.wait(seconds)

    def wait_for(self, selector):

        return self.browser.wait_for(selector)

    def read_text(self, selector):

        return self.browser.read_text(selector)

    def screenshot(self, filename="browser.png"):

        return self.browser.screenshot(filename)
