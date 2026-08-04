# wake_word_advanced.py — FIXED MICROPHONE VERSION

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
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None


class AdvancedWakeWordDetector:

    def __init__(self, callback):

        self.callback = callback

        self.is_running = False

        self.wake_words = [
            "jarvis",
            "hey jarvis",
            "ok jarvis",
            "hi jarvis"
        ]

        self.model = None

        self.audio = pyaudio.PyAudio() if pyaudio is not None else None

        self.input_device_index = None

        self._find_microphone()

        self._load_model()

    # ─────────────────────────────────────
    # FIND WORKING MICROPHONE
    # ─────────────────────────────────────
    def _find_microphone(self):

        if self.audio is None:
            print("\n[WAKE] Audio backend unavailable; wake-word detection disabled.\n")
            return

        print("\n[WAKE] Searching microphones...\n")

        for i in range(self.audio.get_device_count()):

            try:

                info = self.audio.get_device_info_by_index(i)

                if info["maxInputChannels"] > 0:

                    print(f"[MIC] {i}: {info['name']}")

                    if self.input_device_index is None:

                        self.input_device_index = i

            except:
                pass

        print(f"\n[WAKE] Using microphone index: {self.input_device_index}")

    # ─────────────────────────────────────
    # LOAD WHISPER
    # ─────────────────────────────────────
    def _load_model(self):

        if WhisperModel is None:
            print("[WAKE] Faster-Whisper unavailable; wake detector will stay idle")
            return

        print("[WAKE] Loading Whisper model...")

        try:
            self.model = WhisperModel(
                "tiny.en",
                device="cpu",
                compute_type="int8"
            )
            print("[WAKE] ✅ Wake detector ready")
        except Exception:
            self.model = None
            print("[WAKE] Wake detector model could not be initialized")

    # ─────────────────────────────────────
    # CHECK WAKE WORD
    # ─────────────────────────────────────
    def _is_wake_word(self, text):

        text = text.lower().strip()

        for ww in self.wake_words:

            if ww in text:

                return True

        return False

    # ─────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────
    def _listen_loop(self):

        if self.audio is None or self.model is None:
            return

        try:

            stream = self.audio.open(

                format=pyaudio.paInt16,

                channels=1,

                rate=16000,

                input=True,

                input_device_index=self.input_device_index,

                frames_per_buffer=2048
            )

        except Exception as e:

            print(f"\n[WAKE ERROR] Could not open microphone:\n{e}")

            return

        print("\n[WAKE] 🎤 Always listening...\n")

        while self.is_running:

            try:

                frames = []

                for _ in range(int(16000 / 2048 * 2)):

                    data = stream.read(
                        2048,
                        exception_on_overflow=False
                    )

                    frames.append(data)

                audio = np.frombuffer(
                    b"".join(frames),
                    dtype=np.int16
                )

                audio = audio.astype(np.float32) / 32768.0

                segments, _ = self.model.transcribe(

                    audio,

                    language="en",

                    beam_size=1
                )

                text = " ".join(
                    s.text for s in segments
                ).strip().lower()

                if text:

                    print(f"[WAKE HEARD] {text}")

                    if self._is_wake_word(text):

                        print("[WAKE] 🔔 Wake word detected!")

                        threading.Thread(
                            target=self.callback,
                            daemon=True
                        ).start()

                        time.sleep(2)

            except Exception as e:

                print(f"[WAKE ERROR] {e}")

                time.sleep(1)

        stream.stop_stream()

        stream.close()

    # ─────────────────────────────────────
    # START
    # ─────────────────────────────────────
    def start(self):

        self.is_running = True

        threading.Thread(
            target=self._listen_loop,
            daemon=True
        ).start()

    # ─────────────────────────────────────
    # STOP
    # ─────────────────────────────────────
    def stop(self):

        self.is_running = False

        self.audio.terminate()