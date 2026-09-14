# wake_word_advanced.py — FIXED MICROPHONE VERSION

import threading
import time
import numpy as np

try:
    import pyaudio
except Exception:
    pyaudio = None

from faster_whisper import WhisperModel
from microphone_broker import mic_broker, MicState


class AdvancedWakeWordDetector:

    def __init__(self, callback):
        self.callback = callback
        self.is_running = False
        self.wake_words = [
            "tag",
            "hey tag",
            "ok tag",
            "hi tag"
        ]

        self.model = None
        self.audio = pyaudio.PyAudio() if pyaudio is not None else None
        self.input_device_index = None
        self._stream = None

        print("[VOICE] TAG wake listener started")
        self._find_microphone()
        self._load_model()

    def _find_microphone(self):
        if self.audio is None:
            return

        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    if self.input_device_index is None:
                        self.input_device_index = i
                        break
            except:
                pass

        if self.input_device_index is not None:
            try:
                device_name = self.audio.get_device_info_by_index(self.input_device_index)["name"]
                print(f"[VOICE] Microphone device detected: {device_name}")
            except:
                pass

    def _load_model(self):
        print("[WAKE] Loading Whisper model...")
        self.model = WhisperModel(
            "tiny.en",
            device="cpu",
            compute_type="int8"
        )
        print("[WAKE] ✅ TAG wake detector ready")

    def _is_wake_word(self, text):
        text = text.lower().strip()
        for ww in self.wake_words:
            if ww in text:
                return True
        return False

    def _listen_loop(self):
        if self.audio is None:
            if pyaudio is not None:
                self.audio = pyaudio.PyAudio()
                self._find_microphone()
            else:
                print("[WAKE ERROR] PyAudio is unavailable in this environment.")
                return

        acquired = mic_broker.acquire("AdvancedWakeWordDetector", MicState.WAKE_LISTENING)
        if not acquired:
            print("[WAKE ERROR] Wake word loop failed to acquire microphone resource.")
            return

        try:
            self._stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=2048
            )
        except Exception as e:
            print(f"\n[WAKE ERROR] Could not open microphone:\n{e}")
            mic_broker.release("AdvancedWakeWordDetector")
            return

        while self.is_running:
            try:
                frames = []
                for _ in range(int(16000 / 2048 * 1.5)):
                    if not self.is_running:
                        break
                    try:
                        data = self._stream.read(2048, exception_on_overflow=False)
                        frames.append(data)
                    except:
                        break

                if not self.is_running or not frames:
                    break

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
                        print("[VOICE] TAG wake word detected")

                        self.suspend()

                        threading.Thread(
                            target=self.callback,
                            daemon=True
                        ).start()
                        break

            except Exception as e:
                print(f"[WAKE ERROR] {e}")
                time.sleep(1)

        self._cleanup_stream()

    def _cleanup_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
            self._stream = None

        if self.audio is not None:
            try:
                self.audio.terminate()
            except:
                pass
            self.audio = None

    def suspend(self):
        print("[VOICE] TAG wake listener suspended")
        self.is_running = False
        self._cleanup_stream()
        mic_broker.release("AdvancedWakeWordDetector")

    def resume(self):
        print("[VOICE] TAG wake listener resumed")
        self.start()

    def start(self):
        self.is_running = True
        threading.Thread(
            target=self._listen_loop,
            daemon=True
        ).start()

    def stop(self):
        self.is_running = False
        self._cleanup_stream()
