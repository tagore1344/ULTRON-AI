# adaptive_programming/programming_benchmark.py
"""
Programming benchmarks — executable verification of coding ability.

Each benchmark has a task, expected properties, tests, and pass/fail criteria.
"""
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

# ULTRON_REPO_ROOT lets a sandboxed copy of this package keep targeting the real
# repository for benchmark verification (sandbox isolation support).
REPO_ROOT = Path(__file__).resolve().parent.parent
import os as _os
if _os.environ.get("ULTRON_REPO_ROOT"):
    REPO_ROOT = Path(_os.environ["ULTRON_REPO_ROOT"])


class BenchmarkResult:
    """Outcome of a single benchmark run."""

    def __init__(self, name: str):
        self.name = name
        self.run_id = f"bench_{uuid.uuid4().hex[:8]}"
        self.passed = False
        self.score = 0.0
        self.details = ""
        self.duration_sec = 0.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "run_id": self.run_id,
            "passed": self.passed,
            "score": round(self.score, 3),
            "details": self.details,
            "duration_sec": round(self.duration_sec, 2),
        }


class ProgrammingBenchmark:
    """Suite of programming benchmarks with executable verification."""

    def __init__(self):
        self._benchmarks: Dict[str, callable] = {
            "syntax_validation": self._benchmark_syntax_validation,
            "pattern_matching": self._benchmark_pattern_matching,
            "file_discovery": self._benchmark_file_discovery,
            "code_comprehension": self._benchmark_code_comprehension,
        }

    def run_all(self) -> List[BenchmarkResult]:
        """Run all benchmarks and return results."""
        results = []
        for name, fn in self._benchmarks.items():
            start = time.perf_counter()
            result = BenchmarkResult(name)
            try:
                fn(result)
            except Exception as e:
                result.details = f"Error: {e}"
                logger.error("Benchmark %s failed: %s", name, e)
            result.duration_sec = time.perf_counter() - start
            results.append(result)
        return results

    def run_benchmark(self, name: str) -> Optional[BenchmarkResult]:
        """Run a single benchmark by name."""
        fn = self._benchmarks.get(name)
        if not fn:
            return None
        start = time.perf_counter()
        result = BenchmarkResult(name)
        try:
            fn(result)
        except Exception as e:
            result.details = f"Error: {e}"
        result.duration_sec = time.perf_counter() - start
        return result

    def _benchmark_syntax_validation(self, result: BenchmarkResult):
        """Verify Python syntax validation works correctly."""
        from adaptive_programming.patch_engine import PatchEngine
        engine = PatchEngine()

        # Valid code should pass
        ok, err = engine.validate_python_syntax("def foo(): return 42")
        valid_ok = ok

        # Invalid code should fail
        ok, err = engine.validate_python_syntax("def foo(: return 42")
        invalid_rejected = not ok

        result.passed = valid_ok and invalid_rejected
        result.score = (valid_ok + invalid_rejected) / 2
        result.details = f"valid_passed={valid_ok}, invalid_rejected={invalid_rejected}"

    def _benchmark_pattern_matching(self, result: BenchmarkResult):
        """Verify code search pattern matching."""
        from adaptive_programming.code_search import CodeSearch
        search = CodeSearch()

        # Search for a known pattern in the repo
        matches = search.search_pattern(r"def think\(self", max_results=5)
        found_brain = len(matches) > 0

        # Search for function definitions
        matches = search.find_function("main", file_pattern="*.py")
        found_main = len(matches) > 0

        result.passed = found_brain
        result.score = (found_brain + found_main) / 2
        result.details = f"found_brain={found_brain}, found_main={found_main}"

    def _benchmark_file_discovery(self, result: BenchmarkResult):
        """Verify repository file discovery."""
        from adaptive_programming.code_search import CodeSearch
        search = CodeSearch()

        structure = search.get_project_structure()
        has_core = "core" in structure
        has_backend = "backend" in structure
        total_files = sum(len(v) for v in structure.values())

        result.passed = has_core and has_backend and total_files > 10
        result.score = min(1.0, total_files / 50)
        result.details = f"total_files={total_files}, has_core={has_core}, has_backend={has_backend}"

    def _benchmark_code_comprehension(self, result: BenchmarkResult):
        """Verify code reading and comprehension."""
        from adaptive_programming.repository_engine import RepositoryEngine
        repo = RepositoryEngine()

        # Read a known file
        content = repo.read_file("core/brain/ai_brain.py")
        has_brain_class = "class AIBrain" in content
        has_think = "def think" in content

        # List files
        files = repo.list_files("*.py", directory="core", max_results=50)
        found_files = len(files) > 0

        result.passed = has_brain_class and has_think and found_files
        result.score = (has_brain_class + has_think + found_files) / 3
        result.details = f"has_brain_class={has_brain_class}, has_think={has_think}, found_files={found_files}"


benchmark_suite = ProgrammingBenchmark()
