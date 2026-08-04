# speech_engine_advanced.py
import os
import threading
import time

try:
    import numpy as np
except Exception:
    np = None

try:
    import pyaudio
except Exception:
    pyaudio = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None


class AdvancedSpeechEngine:

    def __init__(self):
        print("[SPEECH] Initializing Ultron Voice Engine with Faster-Whisper...")

        self.tts = None
        if pyttsx3 is not None:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 180)
                self.tts.setProperty('volume', 1.0)
            except Exception:
                self.tts = None

        self.format = getattr(pyaudio, "paInt16", None) if pyaudio is not None else None
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio = pyaudio.PyAudio() if pyaudio is not None else None

        self.input_device_index = None
        if self.audio is not None:
            self._find_microphone()

        self.model = None
        if WhisperModel is not None:
            try:
                self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            except Exception:
                self.model = None

        print("[SPEECH] ✅ Faster-Whisper Voice Engine Active!" if self.model is not None else "[SPEECH] Fallback voice engine active (local speech features disabled).")

    def _find_microphone(self):
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    if self.input_device_index is None:
                        self.input_device_index = i
                        break
            except:
                pass

    def speak(self, text):
        """Standard Text to Speech Engine Output"""
        print(f"[ULTRON TTS]: {text}")
        if pyttsx3 is None:
            return

        def _say():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 185)
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

        threading.Thread(target=_say, daemon=True).start()

    def listen(self, timeout=7):
        """
        Listens to microphone data and decodes via Faster-Whisper
        Ensures a clean response on the first command.
        """
        if self.audio is None or self.model is None:
            return ""

        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk
            )
        except Exception as e:
            print(f"[AUDIO ERROR] Could not open capture hardware: {e}")
            return ""

        print("[ULTRON] Awaiting your direct command...")
        frames = []
        start_time = time.time()
        silence_threshold = 400
        silent_chunks = 0
        has_spoken = False

        while time.time() - start_time < timeout:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)

                audio_data = np.frombuffer(data, dtype=np.int16)
                amplitude = np.abs(audio_data).mean()

                if amplitude > silence_threshold:
                    has_spoken = True
                    silent_chunks = 0
                else:
                    if has_spoken:
                        silent_chunks += 1

                if has_spoken and silent_chunks > 25:
                    break
            except Exception:
                break

        stream.stop_stream()
        stream.close()

        if not frames:
            return ""

        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(audio_np, beam_size=1)
        text = " ".join([seg.text for seg in segments]).strip()

        return text