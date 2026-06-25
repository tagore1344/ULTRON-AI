# test_app_controller.py
import time
from app_controller import AppController
from speech_engine_advanced import AdvancedSpeechEngine

print("=== Testing App Controller ===")

# Initialize
speech = AdvancedSpeechEngine()
app_controller = AppController(speech)

# Test 1: Open Notepad
print("Test 1: Opening Notepad...")
app_controller.open_app("notepad")
time.sleep(2)

# Test 2: Open Calculator
print("Test 2: Opening Calculator...")
app_controller.open_app("calculator")
time.sleep(2)

# Test 3: Open Chrome
print("Test 3: Opening Chrome...")
app_controller.open_app("chrome")
time.sleep(2)

# Test 4: Take Screenshot
print("Test 4: Taking screenshot...")
app_controller.take_screenshot()
time.sleep(1)

print("=== Test Complete ===")