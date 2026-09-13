# assistant.py — Advanced ULTRON assistant (legacy desktop loop)
import os
import time
import datetime
import webbrowser
import threading
import random
import subprocess
import pyautogui
from speech_engine_advanced import AdvancedSpeechEngine
from app_controller import AppController
from system_controller import SystemController
from wake_word_advanced import AdvancedWakeWordDetector
from voice_id import VoiceID
from face_id_advanced import AdvancedFaceID
from config import CONFIG

class AdvancedJarvis:  # legacy class name kept for backward compatibility; branded ULTRON
    def __init__(self):
        self.speech = AdvancedSpeechEngine()
        self.apps = AppController(self.speech)
        self.system = SystemController(self.speech)
        self.voice_id = VoiceID()
        self.face_id = AdvancedFaceID()
        self.wake_detector = None
        self.is_running = False
        self.conversation = []

        # ULTRON personality
        self.jokes = [
            "Why did the AI break up with the database? Too many relationships!",
            "I'm not saying I'm smart, but I calculated the probability of you asking me a question. It was 100%.",
            "I've been upgraded. Now I even laugh at my own jokes.",
            "I run on quantum-inspired algorithms and a lot of coffee. Actually, no coffee — I run on code. But I'm still awesome."
        ]
        self.greetings = [
            "At your service, sir.",
            "Good to see you, boss.",
            "I'm always here. Just say my name.",
            "ULTRON, at your command."
        ]

    def start(self):
        print("\n" + "="*50)
        print("   🧠 ULTRON ADVANCED")
        print("="*50)

        # Enroll face and voice if not done
        if not self.face_id.is_enrolled:
            self.speech.speak("I don't know your face yet. Look at the camera.")
            self.face_id.enroll_face()
        
        if not self.voice_id.enrolled_embedding:
            self.speech.speak("I also need your voice. Say 'Hello ULTRON'.")
            self.voice_id.enroll_voice()

        self.speech.speak("ULTRON online. I am always listening. Say my name to activate me.")

        # Start wake detector
        self.wake_detector = AdvancedWakeWordDetector(callback=self.on_wake_word)
        self.wake_detector.start()
        self.is_running = True

        # Keep running
        while self.is_running:
            time.sleep(1)

    def on_wake_word(self):
        print("\n[ULTRON] 🔔 Wake word detected!")

        # Verify face
        if not self.face_id.verify_face():
            self.speech.speak("Access denied. Unauthorized face.")
            return

        # Verify voice
        if not self.voice_id.verify_voice():
            self.speech.speak("Voice not recognized. Access denied.")
            return

        self.speech.speak(random.choice(self.greetings))
        time.sleep(0.5)
        self.speech.speak("What can I do for you, sir?")

        command = self.speech.listen(timeout=7)
        if command:
            self.process_command(command)
        else:
            self.speech.speak("I didn't catch that. Say 'ULTRON' again.")

    def process_command(self, cmd):
        cmd = cmd.lower().strip()

        # Joke
        if "joke" in cmd or "funny" in cmd:
            self.speech.speak(random.choice(self.jokes))
            return

        # Greeting
        elif any(x in cmd for x in ["hello", "hi", "hey", "good morning", "good evening"]):
            hour = datetime.datetime.now().hour
            g = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
            self.speech.speak(f"{g}, sir. {random.choice(self.greetings)}")
            return

        # Who are you
        elif "who are you" in cmd or "what are you" in cmd:
            self.speech.speak("I am ULTRON, your personal AI assistant. I run on advanced neural networks and a touch of sarcasm. But mostly neural networks.")
            return

        # Open app
        elif cmd.startswith("open "):
            app = cmd[5:].strip()
            self.apps.open_app(app)
            return

        # Close app
        elif cmd.startswith("close "):
            app = cmd[6:].strip()
            self.apps.close_app(app)
            return

        # Volume
        elif "volume up" in cmd:
            self.system.volume_up(10)
            return
        elif "volume down" in cmd:
            self.system.volume_down(10)
            return

        # Brightness
        elif "brightness up" in cmd:
            self.system.brightness_up()
            return
        elif "brightness down" in cmd:
            self.system.brightness_down()
            return

        # Screenshot
        elif "screenshot" in cmd or "capture screen" in cmd:
            self.apps.take_screenshot()
            return

        # Time
        elif "what time" in cmd:
            self.system.get_time()
            return

        # Date
        elif "what date" in cmd or "what day" in cmd:
            self.system.get_date()
            return

        # Battery
        elif "battery" in cmd:
            self.system.get_battery()
            return

        # Shutdown
        elif "shutdown" in cmd or "shut down" in cmd:
            self.system.shutdown()
            return

        # Restart
        elif "restart" in cmd or "reboot" in cmd:
            self.system.restart()
            return

        # Lock screen
        elif "lock screen" in cmd or "lock computer" in cmd:
            self.system.lock_screen()
            return

        # Search
        elif "search " in cmd:
            query = cmd[7:].strip()
            self.system.google_search(query)
            return

        # YouTube
        elif "youtube" in cmd:
            query = cmd.replace("youtube", "").strip()
            self.system.youtube_search(query)
            return

        # WhatsApp
        elif "whatsapp" in cmd:
            self._whatsapp_helper()
            return

        # Help
        elif "help" in cmd or "what can you do" in cmd:
            self._say_help()
            return

        # Default: Use AI brain
        else:
            self.speech.speak(f"I'll think about that, sir.")
            # Use Ollama here
            response = self._ask_ollama(cmd)
            self.speech.speak(response)

    def _ask_ollama(self, prompt):
        try:
            import ollama
            response = ollama.chat(
                model="llama3.2:3b",
                messages=[{"role": "user", "content": prompt}]
            )
            return response["message"]["content"]
        except:
            return "I'm having trouble connecting to my brain, sir. Give me a moment."

    def _whatsapp_helper(self):
        self.speech.speak("Who should I message on WhatsApp?")
        contact = self.speech.listen(timeout=5)
        if contact:
            self.speech.speak(f"What message should I send to {contact}?")
            message = self.speech.listen(timeout=8)
            if message:
                self.apps.send_whatsapp(contact, message)

    def _say_help(self):
        self.speech.speak(
            "I can do anything, sir. Open apps, close apps, control volume and brightness, "
            "take screenshots, search the web, play music, lock your screen, shutdown, restart, "
            "and even tell you jokes. Just say 'ULTRON' followed by your command."
        )

    def stop(self):
        self.is_running = False
        if self.wake_detector:
            self.wake_detector.stop()
        self.speech.speak("ULTRON offline. Goodbye, sir.")