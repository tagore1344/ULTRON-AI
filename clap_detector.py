# clap_detector.py
import threading
import time
import numpy as np

try:
    import pyaudio
except Exception:
    pyaudio = None

from microphone_broker import mic_broker, MicState


class ClapDetector:
    """Detects double-clap sound signatures to wake the assistant cleanly and non-privileged."""

    def __init__(self, callback, threshold=8000, min_interval=0.15, max_interval=0.8):
        self.callback = callback
        self.threshold = threshold
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.is_running = False
        self.audio = pyaudio.PyAudio() if pyaudio is not None else None
        self.input_device_index = None
        self._stream = None

        # State tracking for double claps
        self._last_clap_time = 0.0

        if self.audio is not None:
            self._find_microphone()

    def _find_microphone(self):
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    self.input_device_index = i
                    break
            except:
                pass

    def _listen_loop(self):
        if self.audio is None:
            if pyaudio is not None:
                self.audio = pyaudio.PyAudio()
                self._find_microphone()
            else:
                print("[CLAP ERROR] PyAudio is unavailable in this environment.")
                return

        # Exclusively acquire the microphone resource lock
        acquired = mic_broker.acquire("ClapDetector", MicState.WAKE_LISTENING)
        if not acquired:
            print("[CLAP ERROR] Failed to acquire microphone resource lock.")
            return

        print("[VOICE] Clap detector active")

        try:
            self._stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=1024
            )
        except Exception as e:
            print(f"[CLAP ERROR] Could not open microphone: {e}")
            mic_broker.release("ClapDetector")
            return

        while self.is_running:
            try:
                data = self._stream.read(1024, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)

                # Calculate peak amplitude
                peak = np.abs(audio_data).max()

                if peak > self.threshold:
                    now = time.time()
                    elapsed = now - self._last_clap_time

                    if self._last_clap_time > 0 and elapsed >= self.min_interval and elapsed <= self.max_interval:
                        print("[VOICE] Clap detected")

                        # Double-clap valid trigger confirmed, suspend and fire callback
                        self.suspend()

                        threading.Thread(target=self.callback, daemon=True).start()
                        break
                    else:
                        # Log first clap spike
                        self._last_clap_time = now

            except Exception as e:
                print(f"[CLAP ERROR] Loop exception: {e}")
                time.sleep(0.5)

        self._cleanup()

    def _cleanup(self):
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

    # ==============================================================================
    # SUSPEND & RESUME
    # ==============================================================================

    def suspend(self):
        """Releases mic resource and suspends background thread."""
        self.is_running = False
        self._cleanup()
        mic_broker.release("ClapDetector")

    def resume(self):
        """Re-acquires the mic and restarts listening."""
        self.start()

    def start(self):
        self.is_running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop(self):
        self.is_running = False
        self._cleanup()
