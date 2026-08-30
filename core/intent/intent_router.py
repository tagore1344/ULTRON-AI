# core/intent/intent_router.py — Rule-based intent detection
import re
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
        cleaned_text = self.clean_text(text)

        # 1. Match compound pattern: "open <app> and send a message to <recipient> as <message>"
        compound_pattern = re.compile(
            r"^(?:open|launch|start|run)\s+([a-zA-Z0-9 _.-]+?)\s+and\s+send\s+a\s+message\s+to\s+([a-zA-Z0-9 _.-]+?)\s+as\s+(.+)$",
            re.IGNORECASE
        )
        match = compound_pattern.match(cleaned_text)
        if match:
            app_target = match.group(1).lower().strip()
            recipient = match.group(2).strip()
            message = match.group(3).strip()

            return {
                "intent": "composite",
                "actions": [
                    {"intent": "app.open", "target": app_target, "raw_text": f"open {app_target}"},
                    {"intent": "app.send_message", "recipient": recipient, "message": message, "app": app_target, "raw_text": f"send a message to {recipient} as {message}"}
                ],
                "raw_text": cleaned_text
            }

        # 2. Match direct pattern: "send a message to <recipient> as <message>"
        send_direct_pattern = re.compile(
            r"^send\s+a\s+message\s+to\s+([a-zA-Z0-9 _.-]+?)\s+as\s+(.+)$",
            re.IGNORECASE
        )
        match_direct = send_direct_pattern.match(cleaned_text)
        if match_direct:
            recipient = match_direct.group(1).strip()
            message = match_direct.group(2).strip()
            return {
                "intent": "app.send_message",
                "recipient": recipient,
                "message": message,
                "app": "whatsapp",
                "raw_text": cleaned_text
            }

        # 3. Standard rule-based keyword triggers
        for intent, keywords in self.intent_map.items():
            for keyword in keywords:
                if keyword in cleaned_text:
                    target = cleaned_text.replace(keyword, "").strip()
                    return {
                        "intent": intent,
                        "target": target,
                        "raw_text": cleaned_text,
                    }

        return {
            "intent": INTENT_CHAT,
            "target": cleaned_text,
            "raw_text": cleaned_text,
        }
