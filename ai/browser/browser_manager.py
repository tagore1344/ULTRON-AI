from playwright.sync_api import sync_playwright


class BrowserManager:

    def __init__(self):

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):

        if self.browser:
            return

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False
        )

        self.context = self.browser.new_context()

        self.page = self.context.new_page()

        print("[BROWSER] Started")

    def open(self, url):

        self.start()

        print(f"[BROWSER] Opening {url}")

        self.page.goto(url)

        return True

    def click(self, selector):

        self.page.locator(selector).click()

        return True

    def type(self, selector, text):

        self.page.locator(selector).fill(text)

        return True

    def press(self, selector, key):

        self.page.locator(selector).press(key)

        return True

    def wait(self, seconds):

        self.page.wait_for_timeout(seconds * 1000)

        return True

    def wait_for(self, selector):

        self.page.locator(selector).wait_for()

        return True

    def read_text(self, selector):

        return self.page.locator(selector).inner_text()

    def screenshot(self, filename="browser.png"):

        self.page.screenshot(path=filename)

        print(f"[BROWSER] Screenshot saved: {filename}")

        return filename

    def current_url(self):

        if self.page:
            return self.page.url

        return None

    def refresh(self):

        self.page.reload()

        return True

    def back(self):

        self.page.go_back()

        return True

    def forward(self):

        self.page.go_forward()

        return True

    def new_tab(self):

        self.page = self.context.new_page()

        return True

    def close_tab(self):

        self.page.close()

        return True

    def close(self):

        if self.browser:

            self.browser.close()

            self.playwright.stop()

            self.browser = None
            self.context = None
            self.page = None

            print("[BROWSER] Closed")