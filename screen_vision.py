# screen_vision.py

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import pytesseract
except Exception:
    pytesseract = None

from PIL import Image


class ScreenVision:

    def capture_screen(self):

        if pyautogui is None:
            return ""

        screenshot = pyautogui.screenshot()

        path = "data/latest_screen.png"

        screenshot.save(path)

        return path

    def extract_text(self, image_path):

        if pytesseract is None:
            return ""

        image = Image.open(image_path)

        text = pytesseract.image_to_string(image)

        return text

    def analyze_screen(self, _=None):

        image_path = self.capture_screen()

        text = self.extract_text(image_path)

        if not text.strip():

            return "I could not read anything on the screen."

        return f"Screen contains:\n{text[:1000]}"
