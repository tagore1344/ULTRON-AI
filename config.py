# config.py — Re-export from the packaged core.config module
from core.config import CONFIG, DEFAULT_CONFIG, CONFIG_FILE, load_config, save_config

__all__ = ["CONFIG", "DEFAULT_CONFIG", "CONFIG_FILE", "load_config", "save_config"]