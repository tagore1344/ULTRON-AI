from ai.browser.browser_manager import BrowserManager
from ai.browser.skills.search_skill import SearchSkill

browser = BrowserManager()

search = SearchSkill(browser)

search.google("ULTRON AI")

input("Press ENTER to close...")

browser.close()