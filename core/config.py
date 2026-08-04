# core/config.py — Configuration loading and saving
import os
import json

CONFIG_FILE = "assistant_config.json"

DEFAULT_CONFIG = {
    "assistant_name": "ULTRON",
    "wake_words": ["ultron", "hey ultron", "ok ultron", "hi ultron", "yo ultron"],
    "personality": "You are ULTRON, an advanced AI assistant. You are helpful, precise, and always ready to serve.",
    "ollama_model": "llama3.2:3b",
    "ollama_temperature": 0.7,
    "ollama_max_tokens": 300,
    "conversation_limit": 20,
    "vosk_model_path": "vosk-model",
    "whisper_model": "base",
    "whisper_language": "en",
    "whisper_device": "cpu",
    "listen_timeout": 7,
    "energy_threshold": 300,
    "silence_duration": 1.5,
    "use_neural_tts": False,
    "voice_speed": 175,
    "voice_volume": 1.0,
    "voice_index": 0,
    "use_gpu": False,
    "gpu_device": 0,
    "memory_file": "ultron_memory.json",
    "max_memory_items": 50,
    "overlay_position": "bottom-right",
    "overlay_opacity": 0.97,
    "overlay_width": 360,
    "overlay_height": 420,
    "theme": "dark",
    "accent_color": "#00d4ff",
}


def load_config():
    """Load configuration from the JSON file, merging with defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    """Save configuration to the JSON file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass


CONFIG = load_config()