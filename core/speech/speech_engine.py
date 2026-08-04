# core/speech/speech_engine.py — Speech engine wrapper
try:
    from speech_engine_advanced import AdvancedSpeechEngine
except Exception:
    AdvancedSpeechEngine = None


class SpeechEngine:
    """Speech engine that wraps AdvancedSpeechEngine for TTS and STT."""

    def __init__(self):
        self.engine = None
        if AdvancedSpeechEngine is not None:
            try:
                self.engine = AdvancedSpeechEngine()
            except Exception as e:
                print(f"[SPEECH] Engine init failed: {e}")

    def speak(self, text):
        """Speak the given text aloud."""
        if self.engine is not None:
            try:
                self.engine.speak(text)
                return
            except Exception as e:
                print(f"[SPEECH] speak error: {e}")
        print(f"[ULTRON TTS]: {text}")

    def listen(self, timeout=7):
        """Listen for speech and return the transcribed text."""
        if self.engine is not None:
            try:
                return self.engine.listen(timeout=timeout)
            except Exception as e:
                print(f"[SPEECH] listen error: {e}")
        return ""