# intent_router.py

class IntentRouter:

    def __init__(self):

        self.intent_map = {
            "app.open": ["open", "launch", "start", "run"],
            "app.close": ["close", "quit", "exit", "stop"],
            "web.search": ["search", "google", "find"],
            "youtube.search": ["youtube", "play on youtube"],
            "system.volume_up": ["volume up", "increase volume", "raise volume"],
            "system.volume_down": ["volume down", "decrease volume", "lower volume"],
            "system.screenshot": ["screenshot", "capture screen", "take screenshot"],
            "system.time": ["what time", "current time", "time now"],
            "system.date": ["what date", "what day", "today date"]
        }

    def clean_text(self, text):
        remove_words = [
            "please",
            "can you",
            "could you",
            "ultron",  # Swapped from jarvis
            "hey",
            "ok",
            "would you",
            "for me"
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
                        "raw_text": text
                    }

        return {
            "intent": "chat",
            "target": text,
            "raw_text": text
        }