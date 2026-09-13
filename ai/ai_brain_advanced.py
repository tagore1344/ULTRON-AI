# ai_brain_advanced.py — Tony Stark AI Brain
import ollama
import json
import os
import time
from datetime import datetime
from config import CONFIG

class AIBrain:
    def __init__(self):
        self.conversation = []
        self.memory = self._load_memory()
        self.model = CONFIG.get("ollama_model", "llama3.2:3b")
        self.max_tokens = CONFIG.get("ollama_max_tokens", 300)
        self.temperature = CONFIG.get("ollama_temperature", 0.7)
        self._check_ollama()
        self.tony_stark_mode = True  # Enable Tony Stark personality

    def _check_ollama(self):
        try:
            ollama.list()
            print("[BRAIN] ✅ Ollama connected")
        except:
            print("[BRAIN] ❌ Ollama not running. Start with: ollama serve")
            print("[BRAIN]    Running in fallback mode")

    def _load_memory(self):
        # ULTRON memory with one-time migration from the legacy jarvis_memory.json
        mem_file = "ultron_memory.json"
        legacy_file = "jarvis_memory.json"
        if os.path.exists(mem_file):
            try:
                with open(mem_file, "r") as f:
                    return json.load(f)
            except:
                pass
        if os.path.exists(legacy_file):
            try:
                with open(legacy_file, "r") as f:
                    legacy = json.load(f)
                self._migrate_legacy_memory = True
                return legacy
            except:
                pass
        return {"facts": [], "preferences": {}}

    def _save_memory(self):
        mem_file = "ultron_memory.json"
        try:
            with open(mem_file, "w") as f:
                json.dump(self.memory, f, indent=2)
        except:
            pass

    def remember(self, fact: str):
        self.memory["facts"].append({
            "fact": fact,
            "time": datetime.now().isoformat()
        })
        self._save_memory()
        print(f"[BRAIN] Remembered: {fact}")

    def get_memory_context(self):
        facts = self.memory.get("facts", [])
        if not facts:
            return ""
        lines = [f"- {f['fact']}" for f in facts[-10:]]
        return "Things you know about the user:\n" + "\n".join(lines)

    def _is_telugu(self, text: str) -> bool:
        """Check if text contains Telugu characters (Unicode range: 0C00-0C7F)"""
        for char in text:
            if '\u0C00' <= char <= '\u0C7F':
                return True
        return False

    def think(self, user_input: str) -> str:
        """Process user input with Tony Stark AI personality"""
        try:
            # Detect if input is Telugu
            is_telugu = self._is_telugu(user_input)
            
            # Build system prompt with Tony Stark personality
            now = datetime.now().strftime("%A %B %d %Y, %I:%M %p")
            memory_context = self.get_memory_context()

            if is_telugu:
                system_prompt = f"""You are ULTRON, an advanced personal AI assistant. 
Current time: {now}
Date: {datetime.now().strftime('%A, %B %d, %Y')}

{memory_context}

You are:
- Warm, witty, and slightly sarcastic
- Highly intelligent and knowledgeable
- **You understand Telugu and can respond in Telugu**
- Protective of your user
- Concise but not robotic
- A trusted AI companion, not just a tool

Keep responses to 2-4 sentences unless asked for more.
Never say you are a language model or AI. You are ULTRON.

**IMPORTANT:** The user is speaking Telugu. Respond in Telugu.
"""
            else:
                system_prompt = f"""You are ULTRON, an advanced personal AI assistant. 
Current time: {now}
Date: {datetime.now().strftime('%A, %B %d, %Y')}

{memory_context}

You are:
- Warm, witty, and slightly sarcastic
- Highly intelligent and knowledgeable
- **You understand Telugu and can respond in Telugu if the user speaks Telugu**
- Protective of your user
- Concise but not robotic
- A trusted AI companion, not just a tool

Keep responses to 2-4 sentences unless asked for more.
Never say you are a language model or AI. You are ULTRON.

The user is speaking English. Respond in English.
"""

            # Build conversation
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add last 10 messages for context
            for msg in self.conversation[-10:]:
                messages.append(msg)

            # Add current user input
            messages.append({"role": "user", "content": user_input})

            print("[BRAIN] Thinking with Tony Stark AI...")
            start = time.time()

            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            )

            elapsed = time.time() - start
            reply = response["message"]["content"].strip()
            print(f"[BRAIN] Reply in {elapsed:.2f}s")

            # Save to conversation
            self.conversation.append({"role": "user", "content": user_input})
            self.conversation.append({"role": "assistant", "content": reply})

            # Auto-remember important things
            self._auto_remember(user_input)

            return reply

        except Exception as e:
            print(f"[BRAIN] Error: {e}")
            return "I'm having trouble connecting to my brain, sir. Give me a moment to reboot."

    def _auto_remember(self, text: str):
        triggers = [
            "my name is", "i am", "i live in",
            "i like", "i love", "i hate",
            "remember that", "don't forget",
            "my favorite", "my birthday"
        ]
        for t in triggers:
            if t in text.lower():
                self.remember(text)
                break

    def clear_conversation(self):
        self.conversation = []
        print("[BRAIN] Conversation cleared")

    def get_conversation_history(self):
        return self.conversation