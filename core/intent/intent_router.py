# core/intent/intent_router.py — Rule-based intent detection
from core.constants import INTENT_CHAT


class IntentRouter:
    """Detects user intent from text using keyword matching."""

    def __init__(self):
        self.intent_map = {
            "app.open": ["open", "launch", "start", "run"],
            "app.close": ["close", "quit", "exit", "stop"],
            "web.search": ["search", "google", "find"],
            "youtube.search": ["youtube", "play on youtube"],
            "system.volume_up": ["volume up", "increase volume", "raise volume"],
            "system.volume_down": ["volume down", "decrease volume", "lower volume"],
            "system.brightness_up": ["brightness up", "increase brightness", "raise brightness"],
            "system.brightness_down": ["brightness down", "decrease brightness", "lower brightness"],
            "system.screenshot": ["screenshot", "capture screen", "take screenshot"],
            "system.screen_read": ["read screen", "what is on screen", "what's on screen"],
            "system.time": ["what time", "current time", "time now"],
            "system.date": ["what date", "what day", "today date"],
            "system.battery": ["battery", "battery level", "battery percent"],
            "system.info": ["system info", "cpu usage", "ram usage", "system status"],
        }

    def clean_text(self, text):
        remove_words = [
            "please",
            "can you",
            "could you",
            "ultron",
            "hey",
            "ok",
            "would you",
            "for me",
        ]

        text = text.lower()
        for word in remove_words:
            text = text.replace(word, "")

        return text.strip()

    def detect(self, text):
        text = self.clean_text(text)

        for intent, keywords in self.intent_map.items():
            for keyword in keywords:
                if keyword in text:
                    target = text.replace(keyword, "").strip()
                    return {
                        "intent": intent,
                        "target": target,
                        "raw_text": text,
                    }

        return {
            "intent": INTENT_CHAT,
            "target": text,
            "raw_text": text,
        }