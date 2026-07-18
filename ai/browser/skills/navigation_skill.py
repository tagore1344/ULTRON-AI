from .base_skill import BaseSkill


class NavigationSkill(BaseSkill):

    def open(self, url):

        return self.browser.open(url)

    def back(self):

        return self.browser.back()

    def forward(self):

        return self.browser.forward()

    def refresh(self):

        return self.browser.refresh()