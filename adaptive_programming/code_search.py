# adaptive_programming/code_search.py
"""
Repository code search — pattern-based discovery with context awareness.
"""
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


class SearchResult:
    """A single search match."""

    def __init__(self, file: str, line: int, content: str, context: str = ""):
        self.file = file
        self.line = line
        self.content = content.strip()
        self.context = context

    def to_dict(self) -> Dict:
        return {
            "file": self.file,
            "line": self.line,
            "content": self.content,
            "context": self.context,
        }


class CodeSearch:
    """Search codebase with regex patterns and structural filtering."""

    def __init__(self, root: Optional[Path] = None):
        self.root = (root or REPO_ROOT).resolve()

    def search_pattern(self, pattern: str, directory: str = "",
                       file_pattern: str = "*.py",
                       max_results: int = 50) -> List[SearchResult]:
        """Search for a regex pattern across the repository."""
        import fnmatch
        base = self.root / directory if directory else self.root
        results = []
        try:
            regex = re.compile(pattern)
        except re.error:
            return []

        for path in sorted(base.rglob(file_pattern)):
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.root))
            parts = Path(rel).parts
            if any(p.startswith(".") or p in ("__pycache__", "node_modules", "venv", ".venv", ".git") for p in parts):
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        context_start = max(0, i - 3)
                        context_end = min(len(lines), i + 2)
                        context = "\n".join(lines[context_start:context_end])
                        results.append(SearchResult(rel, i, line, context))
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue
        return results

    def find_function(self, name: str, file_pattern: str = "*.py") -> List[SearchResult]:
        """Find function/class definitions."""
        return self.search_pattern(
            rf"^\s*(def|class)\s+{re.escape(name)}\b",
            file_pattern=file_pattern,
        )

    def find_imports(self, module: str) -> List[SearchResult]:
        """Find imports of a specific module."""
        return self.search_pattern(
            rf"(?:from\s+{re.escape(module)}\s+import|import\s+{re.escape(module)})",
        )

    def find_error_handlers(self) -> List[SearchResult]:
        """Find try/except blocks that may suppress errors."""
        return self.search_pattern(r"except\s*:", max_results=30)

    def find_todos(self) -> List[SearchResult]:
        """Find TODO/FIXME/HACK markers."""
        return self.search_pattern(r"#\s*(TODO|FIXME|HACK|XXX|BUG)", max_results=30)

    def get_project_structure(self) -> Dict[str, List[str]]:
        """Return directory tree of Python files grouped by top-level dir."""
        structure: Dict[str, List[str]] = {}
        for path in sorted(self.root.rglob("*.py")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.root))
            parts = Path(rel).parts
            if any(p.startswith(".") or p in ("__pycache__", "node_modules", "venv", ".venv") for p in parts):
                continue
            top = parts[0] if len(parts) > 1 else "root"
            structure.setdefault(top, []).append(rel)
        return structure
