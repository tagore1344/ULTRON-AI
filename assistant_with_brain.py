# assistant_with_brain.py
# FIXED THREADING VERSION FOR TAG AI

from transparent_overlay import UltronTopOverlay
from PyQt6.QtWidgets import QApplication
import sys
import os
import time
import random
import threading
import pyautogui

from memory_engine import MemoryEngine
from speech_engine_advanced import AdvancedSpeechEngine
from app_controller import AppController
from system_controller import SystemController
from wake_word_advanced import AdvancedWakeWordDetector
from clap_detector import ClapDetector
from config import CONFIG
from ai_brain_advanced import AIBrain
from intent_router import IntentRouter
from tool_registry import ToolRegistry
from voice_id import VoiceID


class JarvisWithBrain:

    def __init__(self):
        print("\n[BOOT] Initializing TAG Operating Matrix...\n")
        self.memory = MemoryEngine()
        self.overlay = None
        self.speech = AdvancedSpeechEngine()
        self.apps = AppController(self.speech)
        self.system = SystemController(self.speech)
        self.brain = AIBrain()
        self.router = IntentRouter()
        self.tools = ToolRegistry(self)
        self.voice_verifier = VoiceID()
        self.wake_detector = None
        self.is_running = False
        self.activation_responses = [
            "Awaiting your command, sir.",
            "Systems operational. I am listening.",
            "Go ahead, sir.",
            "What can I do for you?",
            "TAG is online. Ready."
        ]
        print("[BOOT] TAG components compiled successfully!")

    def inject_overlay(self, overlay_instance):
        self.overlay = overlay_instance
        self.safe_update_overlay("SYSTEM ONLINE", "idle")

    def safe_update_overlay(self, text, state="idle"):
        if self.overlay:
            from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
            QMetaObject.invokeMethod(
                self.overlay,
                "update_status",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text),
                Q_ARG(str, state)
            )

    def start(self):
        print("\n" + "=" * 60)
        print("          🧠 TAG AI AGENT (VOICE LOCKED)")
        print("=" * 60)
        threading.Thread(target=self._run_speech_greeting, daemon=True).start()

        wake_mode = CONFIG.get("wake_mode", "wake_word")
        self.clap_detector = None
        self.wake_detector = None
        if wake_mode == "clap":
            self.clap_detector = ClapDetector(callback=self.on_wake_word)
            self.clap_detector.start()
        else:
            self.wake_detector = AdvancedWakeWordDetector(callback=self.on_wake_word)
            self.wake_detector.start()

        self.is_running = True
        print("\n[TAG] Running and monitoring audio feed...\n")

    def _run_speech_greeting(self):
        self.speech.speak("TAG online. Systems secured to your biometric voice print.")

    def on_wake_word(self):
        print("\n[TAG] Wake word phrase detected. Running voice authentication...")
        self.safe_update_overlay("VERIFYING VOICE...", "thinking")
        is_verified = self.voice_verifier.verify_speaker()

        if not is_verified:
            print("[SECURITY ALERT] Wake word spoken by unverified voice. Access denied.")
            self.safe_update_overlay("ACCESS DENIED", "listening")
            time.sleep(2)
            self.safe_update_overlay("SYSTEM SECURED", "idle")
            if self.wake_detector:
                self.wake_detector.resume()
            return

        print("[SECURITY] Biometric match confirmed. Access granted.")
        self.safe_update_overlay("LISTENING...", "listening")
        self.speech.speak(random.choice(self.activation_responses))
        time.sleep(0.4)
        command = self.speech.listen(timeout=7)

        if not command:
            self.safe_update_overlay("SYSTEM IDLE", "idle")
            self.speech.speak("I didn't hear a command.")
            if self.wake_detector:
                self.wake_detector.resume()
            return

        print(f"\n[COMMAND] {command}")
        self.process_command(command)
        if self.wake_detector:
            self.wake_detector.resume()

    def process_command(self, cmd):
        try:
            cmd = cmd.lower().strip()
            print(f"\n[PROCESSING] {cmd}")

            if "my name is" in cmd:
                name = cmd.replace("my name is", "").strip()
                self.memory.set_user_name(name)
                self.speech.speak(f"Identity signature saved. I will remember that, {name}.")
                self.safe_update_overlay("SYSTEM IDLE", "idle")
                return

            if "what is my name" in cmd:
                name = self.memory.get_user_name()
                if name:
                    self.speech.speak(f"Your designation is {name}.")
                else:
                    self.speech.speak("I do not have your name registered in my logs.")
                self.safe_update_overlay("SYSTEM IDLE", "idle")
                return

            if cmd.startswith("remember that"):
                note = cmd.replace("remember that", "").strip()
                self.memory.add_note(note)
                self.speech.speak("Data point committed to memory core.")
                self.safe_update_overlay("SYSTEM IDLE", "idle")
                return

            if "what do you remember" in cmd:
                notes = self.memory.get_notes()
                if not notes:
                    self.speech.speak("My active database registers no stored logs.")
                else:
                    joined = ". ".join(notes[-5:])
                    self.speech.speak(f"Retrieved entries: {joined}")
                self.safe_update_overlay("SYSTEM IDLE", "idle")
                return

            intent_data = self.router.detect(cmd)
            intent = intent_data["intent"]
            target = intent_data["target"]
            print(f"\n[INTENT] {intent_data}")
            self.safe_update_overlay("EXECUTING...", "thinking")
            executed = self.tools.execute(intent, target)

            if not executed:
                print("\n[AI CORE] Thinking...")
                self.safe_update_overlay("THINKING...", "thinking")
                user_name = self.memory.get_user_name()
                contextual_prompt = cmd
                if user_name:
                    contextual_prompt = f"\nUser name: {user_name}\nUser message:\n{cmd}\n"
                response = self.brain.think(contextual_prompt)
                self.memory.add_conversation(cmd, response)
                print(f"\n[TAG] {response}")
                self.safe_update_overlay("SPEAKING...", "idle")
                self.speech.speak(response)

            self.safe_update_overlay("SYSTEM IDLE", "idle")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            self.safe_update_overlay("ERROR ANOMALY", "listening")
            self.speech.speak("An anomaly occurred while executing that operation.")
            time.sleep(2)
            self.safe_update_overlay("SYSTEM IDLE", "idle")

    def stop(self):
        print("\n[SHUTDOWN] Powering down TAG cores...\n")
        self.is_running = False
        if self.wake_detector:
            self.wake_detector.stop()
        if self.clap_detector:
            self.clap_detector.stop()
        self.safe_update_overlay("OFFLINE", "listening")
        print("[SHUTDOWN] Complete")