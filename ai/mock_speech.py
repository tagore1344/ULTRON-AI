class MockSpeech:

    def speak(self, text):
        print(f"[SPEAK] {text}")

    def listen(self, timeout=None):
        return input("[LISTEN] > ")