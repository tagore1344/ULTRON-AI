# Manual smoke-test script for AppController.
# Run directly on Windows with the project's optional speech and automation
# dependencies installed. This file is intentionally import-safe for pytest.


def main():
    import time

    from app_controller import AppController
    from speech_engine_advanced import AdvancedSpeechEngine

    print("=== Testing App Controller ===")

    speech = AdvancedSpeechEngine()
    app_controller = AppController(speech)

    print("Test 1: Opening Notepad...")
    app_controller.open_app("notepad")
    time.sleep(2)

    print("Test 2: Opening Calculator...")
    app_controller.open_app("calculator")
    time.sleep(2)

    print("Test 3: Opening Chrome...")
    app_controller.open_app("chrome")
    time.sleep(2)

    print("Test 4: Taking screenshot...")
    app_controller.take_screenshot()
    time.sleep(1)

    print("=== Test Complete ===")


if __name__ == "__main__":
    main()
