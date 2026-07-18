from ai.browser.browser_manager import BrowserManager

browser = BrowserManager()

browser.open("https://www.google.com")

browser.wait(2)

browser.type('textarea[name="q"]', "ULTRON AI")

browser.press('textarea[name="q"]', "Enter")

browser.wait(3)

browser.screenshot("google_results.png")

print("Current URL:", browser.current_url())

input("Press ENTER to close...")

browser.close()