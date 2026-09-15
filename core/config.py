# core/config.py — Canonical TAG configuration loader
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from core.constants import (
    ACCENT_COLOR,
    ASSISTANT_NAME,
    AUDIO_CHANNELS,
    AUDIO_CHUNK,
    AUDIO_RATE,
    ENERGY_THRESHOLD,
    GEMINI_MODEL,
    LISTEN_TIMEOUT,
    LOG_FILE,
    MAX_MEMORY_ITEMS,
    MEMORY_FILE,
    OLLAMA_MODEL,
    OVERLAY_HEIGHT,
    OVERLAY_OPACITY,
    OVERLAY_POSITION,
    OVERLAY_WIDTH,
    SCREENSHOT_PATH,
    SILENCE_DURATION,
    THEME,
    VOICE_INDEX,
    VOICE_SPEED,
    VOICE_VOLUME,
    WAKE_WORDS,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL,
    CONFIG_FILE,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = str(ROOT_DIR / CONFIG_FILE)

DEFAULT_CONFIG: dict[str, Any] = {
    "assistant": {
        "name": ASSISTANT_NAME,
        "wake_words": WAKE_WORDS,
    },
    "models": {
        "gemini": GEMINI_MODEL,
        "ollama": OLLAMA_MODEL,
        "whisper": WHISPER_MODEL,
        "whisper_language": WHISPER_LANGUAGE,
        "whisper_device": WHISPER_DEVICE,
    },
    "audio": {
        "rate": AUDIO_RATE,
        "channels": AUDIO_CHANNELS,
        "chunk": AUDIO_CHUNK,
        "listen_timeout": LISTEN_TIMEOUT,
        "energy_threshold": ENERGY_THRESHOLD,
        "silence_duration": SILENCE_DURATION,
    },
    "voice": {
        "speed": VOICE_SPEED,
        "volume": VOICE_VOLUME,
        "index": VOICE_INDEX,
    },
    "memory": {
        "max_items": MAX_MEMORY_ITEMS,
        "conversation_limit": 20,
        "file": str(ROOT_DIR / MEMORY_FILE),
    },
    "overlay": {
        "position": OVERLAY_POSITION,
        "opacity": OVERLAY_OPACITY,
        "width": OVERLAY_WIDTH,
        "height": OVERLAY_HEIGHT,
        "theme": THEME,
        "accent_color": ACCENT_COLOR,
    },
    "files": {
        "config": CONFIG_FILE,
        "memory": str(ROOT_DIR / MEMORY_FILE),
        "screenshot": str(ROOT_DIR / SCREENSHOT_PATH),
        "log": str(ROOT_DIR / LOG_FILE),
    },
    "apps": {},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    config_path = Path(path or CONFIG_FILE)
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not config_path.exists():
        return config
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            config = _deep_merge(config, data)
    except (OSError, json.JSONDecodeError):
        pass
    return config


def save_config(config: dict[str, Any], path: str | os.PathLike[str] | None = None) -> bool:
    config_path = Path(path or CONFIG_FILE)
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


CONFIG = load_config()

__all__ = ["CONFIG", "DEFAULT_CONFIG", "CONFIG_FILE", "load_config", "save_config"]
