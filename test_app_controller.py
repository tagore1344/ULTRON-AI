# test_app_controller.py
import time
from app_controller import AppController
from speech_engine_advanced import AdvancedSpeechEngine


def test_app_controller_smoke():
    speech = AdvancedSpeechEngine()
    app_controller = AppController(speech)

    app_controller.open_app("notepad")
    time.sleep(0.1)

    app_controller.open_app("calculator")
    time.sleep(0.1)

    app_controller.open_app("chrome")
    time.sleep(0.1)

    screenshot_name = app_controller.take_screenshot()
    assert isinstance(screenshot_name, str)
    assert screenshot_name.endswith(".png")