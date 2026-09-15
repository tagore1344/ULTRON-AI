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

from microphone_broker import mic_broker, MicState


class AdvancedSpeechEngine:

    def __init__(self):
        print("[SPEECH] Initializing TAG Voice Engine with Faster-Whisper...")

        self.tts = None
        self._tts_lock = threading.Lock()
        if pyttsx3 is not None:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty("rate", 180)
                self.tts.setProperty("volume", 1.0)
                print("[SPEECH] TTS engine ready")
            except Exception as exc:
                print(f"[SPEECH] TTS initialization failed: {exc}")
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
        print(
            "[SPEECH] Faster-Whisper Voice Engine Active (Lazy Loading enabled)!"
            if WhisperModel is not None
            else "[SPEECH] Fallback voice engine active (local speech features disabled)."
        )

    def _find_microphone(self):
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    self.input_device_index = i
                    break
            except Exception:
                pass

    def speak(self, text):
        """Speak using the initialized Windows TTS engine, serialized for reliability."""
        text = str(text).strip()
        if not text:
            return

        print(f"[TAG TTS]: {text}")

        if self.tts is None:
            print("[SPEECH ERROR] TTS engine unavailable; response was printed only.")
            return

        def _say():
            with self._tts_lock:
                try:
                    self.tts.say(text)
                    self.tts.runAndWait()
                except Exception as exc:
                    print(f"[SPEECH ERROR] TTS playback failed: {exc}")
                    # Reinitialize once if the Windows speech engine became stale.
                    try:
                        if pyttsx3 is not None:
                            self.tts = pyttsx3.init()
                            self.tts.setProperty("rate", 180)
                            self.tts.setProperty("volume", 1.0)
                            self.tts.say(text)
                            self.tts.runAndWait()
                    except Exception as retry_exc:
                        print(f"[SPEECH ERROR] TTS retry failed: {retry_exc}")

        threading.Thread(target=_say, daemon=True).start()

    def listen(self, timeout=7):
        if self.audio is None:
            return ""

        acquired = mic_broker.acquire("AdvancedSpeechEngine", MicState.COMMAND_LISTENING)
        if not acquired:
            print("[AUDIO ERROR] Failed to acquire microphone resource lock.")
            return ""

        print("[VOICE] Command listening started")

        if self.model is None and WhisperModel is not None:
            try:
                print("[SPEECH] Lazily loading Whisper model 'tiny.en'...")
                self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
                print("[VOICE] Whisper model ready")
            except Exception as exc:
                print(f"[SPEECH ERROR] Failed to lazily load Whisper model: {exc}")
                self.model = None

        if self.model is None:
            mic_broker.release("AdvancedSpeechEngine")
            return ""

        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk,
            )
        except Exception as exc:
            print(f"[AUDIO ERROR] Could not open capture hardware: {exc}")
            mic_broker.release("AdvancedSpeechEngine")
            return ""

        print("[TAG] Awaiting your direct command...")
        frames = []
        start_time = time.time()
        silence_threshold = 200
        silent_chunks = 0
        has_spoken = False
        max_silent_chunks = 35

        while time.time() - start_time < timeout:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                amplitude = np.abs(audio_data).mean()

                if amplitude > silence_threshold:
                    has_spoken = True
                    silent_chunks = 0
                elif has_spoken:
                    silent_chunks += 1

                if has_spoken and silent_chunks > max_silent_chunks:
                    break
            except Exception:
                break

        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass

        mic_broker.release("AdvancedSpeechEngine")
        print("[VOICE] Command listening stopped")
        print("[VOICE] Microphone released")

        if not frames:
            return ""

        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        try:
            segments, _ = self.model.transcribe(audio_np, beam_size=1)
            text = " ".join(seg.text for seg in segments).strip()
        except Exception as exc:
            print(f"[SPEECH ERROR] Transcription failed: {exc}")
            return ""

        print(f"[VOICE] Transcription: {text}")
        return text
