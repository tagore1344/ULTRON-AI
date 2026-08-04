# core/utils.py — Helper utilities for ULTRON AI
import os
import re
import time
import platform
from datetime import datetime
from functools import wraps


def is_windows():
    """Return True if running on Windows."""
    return platform.system() == "Windows"


def now():
    """Return the current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_text(text):
    """Remove extra whitespace and normalize quotes from text."""
    if not text:
        return ""
    # Replace smart quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def retry(max_attempts=3, delay=1.0):
    """Decorator that retries a function on exception."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"[RETRY] {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def ensure_dir(path):
    """Create a directory path if it doesn't exist."""
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def read_file_safe(path, default=""):
    """Read a text file, returning default on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default


def write_file_safe(path, content):
    """Write text content to a file, creating parent directories as needed."""
    try:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False