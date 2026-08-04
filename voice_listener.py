import threading
import time

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import numpy as np
except Exception:
    np = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None


class VoiceListener:

    def __init__(self, callback):

        self.callback = callback

        self.whisper = None
        if WhisperModel is not None:
            try:
                print("[VOICE] Loading Whisper model...")
                self.whisper = WhisperModel(
                    "medium",
                    device="cpu",
                    compute_type="int8"
                )
                print("[VOICE] Whisper ready!")
            except Exception:
                self.whisper = None
                print("[VOICE] Whisper model unavailable")

        self.sample_rate = 16000

        self.is_running = False

    # ─────────────────────────────────────
    # MAIN LISTEN LOOP
    # ─────────────────────────────────────
    def listen_loop(self):

        if sd is None or self.whisper is None:
            print("[VOICE] Voice listener is unavailable in this environment")
            return

        print("[VOICE] Continuous listening started...")

        while self.is_running:

            try:

                print("[VOICE] Speak now...")

                audio = sd.rec(
                    int(10 * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32'
                )

                sd.wait()

                audio = audio.flatten()

                segments, _ = self.whisper.transcribe(
                    audio,
                    language="en",
                    beam_size=10,
                    best_of=10,
                    temperature=0,
                    vad_filter=True,
                    condition_on_previous_text=False
                )

                text = ""

                for segment in segments:

                    text += segment.text

                text = text.strip().lower()

                if text:

                    print(f"[YOU SAID] {text}")

                    self.callback(text)

            except Exception as e:

                print(f"[VOICE ERROR] {e}")

                time.sleep(1)

    # ─────────────────────────────────────
    # START
    # ─────────────────────────────────────
    def start(self):

        self.is_running = True

        threading.Thread(
            target=self.listen_loop,
            daemon=True
        ).start()

    # ─────────────────────────────────────
    # STOP
    # ─────────────────────────────────────
    def stop(self):

        self.is_running = False