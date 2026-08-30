# adaptive_programming/sandbox_manager.py
"""
Sandbox manager — isolated evaluation of proposed self-improvements.

Creates a real filesystem copy of the adaptive_programming package, applies
candidate patches ONLY inside the sandbox, and executes the benchmark suite
in a subprocess whose import path resolves to the sandboxed package while
ULTRON_REPO_ROOT keeps repository-targeting benchmarks pointed at the real
repository. Production code is never touched during an experiment.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ultron-adaptive")

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_BASE = REPO_ROOT / "backend" / "data" / "adaptive_programming" / "sandboxes"
PACKAGE_NAME = "adaptive_programming"


class Sandbox:
    """A live isolated sandbox instance."""

    def __init__(self, sandbox_id: str, path: Path, repo_root: Path):
        self.sandbox_id = sandbox_id
        self.path = path              # .../sandboxes/<id>/adaptive_programming
        self.repo_root = repo_root    # real repository (read-only benchmark target)
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.destroyed = False

    def to_dict(self) -> Dict:
        return {
            "sandbox_id": self.sandbox_id,
            "path": str(self.path),
            "created_at": self.created_at,
            "destroyed": self.destroyed,
        }


class SandboxManager:
    """Creates, mutates (safely), evaluates, and destroys isolated sandboxes."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base = base_dir or SANDBOX_BASE

    def create_sandbox(self) -> Sandbox:
        """Copy the adaptive_programming package into an isolated directory."""
        sandbox_id = f"sbox_{uuid.uuid4().hex[:8]}"
        parent = self.base / sandbox_id
        target = parent / PACKAGE_NAME
        shutil.copytree(REPO_ROOT / PACKAGE_NAME, target,
                        ignore=shutil.ignore_patterns("__pycache__"))
        sandbox = Sandbox(sandbox_id, target, REPO_ROOT)
        logger.info("Sandbox created: %s at %s", sandbox_id, target)
        return sandbox

    def apply_candidate(self, sandbox: Sandbox, rel_path: str,
                        old_code: str, new_code: str) -> Dict:
        """Apply a candidate patch INSIDE the sandbox only (path-traversal safe)."""
        from adaptive_programming.patch_engine import PatchEngine

        if sandbox.destroyed:
            return {"success": False, "message": "Sandbox already destroyed."}

        # PatchEngine rooted at the sandbox parent so rel_path cannot escape.
        engine = PatchEngine(root=sandbox.path.parent)
        result = engine.apply_patch(f"{PACKAGE_NAME}/{rel_path}", old_code,
                                    new_code)
        if not result.success:
            logger.warning("Sandbox candidate rejected: %s", result.message)
        return result.to_dict()

    def run_benchmarks(self, sandbox: Optional[Sandbox] = None,
                       timeout_seconds: int = 120) -> Dict:
        """Run the executable benchmark suite in a clean subprocess.

        With no sandbox: measures the BASELINE (production package).
        With a sandbox: PYTHONPATH resolves to the sandbox copy while
        ULTRON_REPO_ROOT keeps repository-targeting benchmarks pointed at
        the real repository — production code is never imported or mutated.
        Returns {"success": bool, "results": [...], "mean_score": float}.
        """
        env = os.environ.copy()
        env["ULTRON_REPO_ROOT"] = str(REPO_ROOT)
        if sandbox is not None and not sandbox.destroyed:
            env["PYTHONPATH"] = str(sandbox.path.parent)

        code = (
            "import json, adaptive_programming.programming_benchmark as pb\n"
            "print(json.dumps([r.to_dict() for r in pb.benchmark_suite.run_all()]))"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=timeout_seconds,
                cwd=str(REPO_ROOT), env=env,
            )
        except subprocess.TimeoutExpired:
            logger.error("Benchmark subprocess timed out.")
            return {"success": False, "results": [], "mean_score": 0.0}

        if proc.returncode != 0:
            logger.error("Benchmark subprocess failed: %s",
                         proc.stderr[-500:] if proc.stderr else proc.returncode)
            return {"success": False, "results": [], "mean_score": 0.0}

        try:
            results = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            logger.error("Benchmark subprocess emitted unparseable output.")
            return {"success": False, "results": [], "mean_score": 0.0}

        mean_score = (sum(r.get("score", 0.0) for r in results) / len(results)
                      if results else 0.0)
        return {"success": True, "results": results, "mean_score": mean_score}

    def destroy_sandbox(self, sandbox: Sandbox) -> bool:
        """Remove the sandbox from disk entirely (rollback of failed experiments)."""
        if sandbox.destroyed:
            return True
        sandbox.destroyed = True
        try:
            shutil.rmtree(sandbox.path.parent, ignore_errors=True)
            logger.info("Sandbox destroyed: %s", sandbox.sandbox_id)
            return True
        except Exception as e:
            logger.error("Sandbox teardown failed for %s: %s",
                         sandbox.sandbox_id, e)
            return False


sandbox_manager = SandboxManager()

