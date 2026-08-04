# core/constants.py — Shared constants for the ULTRON AI application

# Assistant identity
ASSISTANT_NAME = "ULTRON"
WAKE_WORDS = ["ultron", "hey ultron", "ok ultron", "hi ultron", "yo ultron"]

# AI model names
GEMINI_MODEL = "gemini-2.5-flash"
OLLAMA_MODEL = "llama3.2:3b"
WHISPER_MODEL = "base"
WHISPER_LANGUAGE = "en"
WHISPER_DEVICE = "cpu"

# File paths
CONFIG_FILE = "assistant_config.json"
MEMORY_FILE = "ultron_memory.json"
SCREENSHOT_PATH = "data/latest_screen.png"
LOG_FILE = "ultron.log"

# Audio settings
AUDIO_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK = 1024
LISTEN_TIMEOUT = 7
ENERGY_THRESHOLD = 300
SILENCE_DURATION = 1.5

# Voice settings
VOICE_SPEED = 175
VOICE_VOLUME = 1.0
VOICE_INDEX = 0

# Memory settings
MAX_MEMORY_ITEMS = 50
CONVERSATION_LIMIT = 20

# Overlay settings
OVERLAY_POSITION = "bottom-right"
OVERLAY_OPACITY = 0.97
OVERLAY_WIDTH = 360
OVERLAY_HEIGHT = 420
THEME = "dark"
ACCENT_COLOR = "#00d4ff"

# Intent keywords
INTENT_CHAT = "chat"
INTENT_TIME = "time"
INTENT_DATE = "date"
INTENT_VOLUME_UP = "volume_up"
INTENT_VOLUME_DOWN = "volume_down"
INTENT_BRIGHTNESS_UP = "brightness_up"
INTENT_BRIGHTNESS_DOWN = "brightness_down"
INTENT_OPEN_APP = "open_app"
INTENT_SCREENSHOT = "screenshot"
INTENT_SCREEN_READ = "screen_read"
INTENT_BATTERY = "battery"
INTENT_SYSTEM_INFO = "system_info"