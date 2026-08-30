# adaptive_programming/repository_engine.py
"""
Repository inspection engine — provides codebase-aware capabilities.

All operations are local filesystem reads (and targeted writes via patch_engine).
No network calls. No shell injection. Paths are validated against the repo root.
"""
import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

# ULTRON_REPO_ROOT lets a sandboxed copy of this package keep targeting the real
# repository for benchmark verification (sandbox isolation support).
REPO_ROOT = Path(__file__).resolve().parent.parent
import os as _os
if _os.environ.get("ULTRON_REPO_ROOT"):
    REPO_ROOT = Path(_os.environ["ULTRON_REPO_ROOT"])


class RepositoryEngine:
    """Read-only repository inspection with path safety and structure awareness."""

    def __init__(self, root: Optional[Path] = None):
        self.root = (root or REPO_ROOT).resolve()

    def _safe_path(self, rel_path: str) -> Path:
        target = (self.root / rel_path).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"Path traversal blocked: {rel_path}")
        return target

    def read_file(self, rel_path: str, limit: int = 5000) -> str:
        path = self._safe_path(rel_path)
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:limit]

    def file_exists(self, rel_path: str) -> bool:
        try:
            return self._safe_path(rel_path).is_file()
        except ValueError:
            return False

    def list_files(self, pattern: str = "*.py", directory: str = "", max_results: int = 200) -> List[str]:
        base = self.root / directory if directory else self.root
        if not base.exists():
            return []
        results = []
        for path in sorted(base.rglob(pattern)):
            if path.is_file():
                rel = str(path.relative_to(self.root))
                parts = Path(rel).parts
                if any(p.startswith(".") or p in ("__pycache__", "node_modules", "venv", ".venv") for p in parts):
                    continue
                results.append(rel)
                if len(results) >= max_results:
                    break
        return results
