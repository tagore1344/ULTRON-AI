# speech_engine_advanced.py
import os
import threading
import time
import numpy as np
import pyaudio
import pyttsx3
from faster_whisper import WhisperModel


class AdvancedSpeechEngine:

    def __init__(self):
        print("[SPEECH] Initializing Ultron Voice Engine with Faster-Whisper...")
        
        # Initialize TTS Engine
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 180)
        self.tts.setProperty('volume', 1.0)
        
        # Audio Recording Parameters
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()
        
        # Locate Best Input Device
        self.input_device_index = None
        self._find_microphone()
        
        # Load Faster-Whisper for high accuracy command processing
        # Change device to "cuda" if your GPU is configured with cuDNN
        self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        print("[SPEECH] ✅ Faster-Whisper Voice Engine Active!")

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
        # Run TTS inside an isolated thread step to avoid locking port audio
        def _say():
            engine = pyttsx3.init()
            engine.setProperty('rate', 185)
            engine.say(text)
            engine.runAndWait()
            
        threading.Thread(target=_say).start()

    def listen(self, timeout=7):
        """
        Listens to microphone data and decodes via Faster-Whisper
        Ensures a clean response on the first command.
        """
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
        silence_threshold = 400  # Amplitude indicator
        silent_chunks = 0
        has_spoken = False

        while time.time() - start_time < timeout:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                
                # Simple energy check to evaluate early stopping if you stop talking
                audio_data = np.frombuffer(data, dtype=np.int16)
                amplitude = np.abs(audio_data).mean()
                
                if amplitude > silence_threshold:
                    has_spoken = True
                    silent_chunks = 0
                else:
                    if has_spoken:
                        silent_chunks += 1
                
                # Cut listening early if conversation has ended natively
                if has_spoken and silent_chunks > 25: 
                    break
            except:
                break

        # Stop and clean up microphone resources safely
        stream.stop_stream()
        stream.close()

        if not frames:
            return ""

        # Processing audio stack
        audio_bytes = b"".join(frames)
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # Transcribe audio data via Faster-Whisper
        segments, _ = self.model.transcribe(audio_np, beam_size=1)
        text = " ".join([seg.text for seg in segments]).strip()
        
        return text