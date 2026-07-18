from ai.browser.browser_manager import BrowserManager

browser = BrowserManager()

browser.open("https://www.google.com")

input("Press ENTER after Google opens...")

print(browser.current_url())

browser.close()