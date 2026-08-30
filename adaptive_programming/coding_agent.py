# adaptive_programming/coding_agent.py
"""
Coding Agent — command-driven programming workflow on top of the existing stack.

User Command
  -> intent classification
  -> policy validation (existing PolicyEngine)
  -> repository inspection (RepositoryEngine / CodeSearch)
  -> locate failing test / relevant code
  -> run test, capture failure (TestEngine)
  -> generate fix via cognition (AIBrain through existing provider orchestration)
  -> apply patch with syntax validation (PatchEngine)
  -> re-run test; iterate up to max_iterations (bounded, no infinite loops)
  -> regression run
  -> record experience + evidence-based capability metrics
"""
import logging
import re
import time
import uuid
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ultron-adaptive")

from adaptive_programming.repository_engine import RepositoryEngine
from adaptive_programming.code_search import CodeSearch
from adaptive_programming.patch_engine import PatchEngine
from adaptive_programming.test_engine import TestEngine
from adaptive_programming.capability_registry import capability_registry
from adaptive_programming.experience_tracker import experience_tracker

try:
    from core.brain.ai_brain import AIBrain
except Exception:
    AIBrain = None

try:
    from core.agent.policy_engine import PolicyEngine
except Exception:
    PolicyEngine = None


class CodingResult:
    """Structured outcome of a coding-agent task."""

    def __init__(self, task_id: str, command: str):
        self.task_id = task_id
        self.command = command
        self.task_type = "unknown"
        self.success = False
        self.steps: List[Dict] = []
        self.files_modified: List[str] = []
        self.iterations = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.root_cause = ""
        self.summary = ""
        self.duration_sec = 0.0

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "command": self.command,
            "task_type": self.task_type,
            "success": self.success,
            "steps": self.steps,
            "files_modified": self.files_modified,
            "iterations": self.iterations,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "root_cause": self.root_cause,
            "summary": self.summary,
            "duration_sec": round(self.duration_sec, 2),
        }


class CodingAgent:
    """Repository-aware programming agent with a real, bounded debugging loop."""

    MAX_ITERATIONS_DEFAULT = 3

    def __init__(self, brain=None, policy=None):
        self.repo = RepositoryEngine()
        self.search = CodeSearch()
        self.patcher = PatchEngine()
        self.tester = TestEngine()
        self.brain = brain or (AIBrain() if AIBrain is not None else None)
        self.policy = policy or (PolicyEngine() if PolicyEngine is not None else None)

    # ==== INTENT ====
    def classify_task(self, command: str) -> str:
        """Map a natural-language command to a task type."""
        c = command.lower()
        if any(k in c for k in ("fix", "debug", "failing test", "broken", "error")):
            return "bug_fix"
        if any(k in c for k in ("test", "coverage")):
            return "test_generation"
        if any(k in c for k in ("refactor", "clean", "restructure")):
            return "refactor"
        if any(k in c for k in ("explain", "why", "how does", "understand")):
            return "explanation"
        if any(k in c for k in ("add", "build", "implement", "create")):
            return "feature"
        return "general"

    def _step(self, result: CodingResult, action: str, detail: str = "") -> None:
        result.steps.append({"action": action, "detail": detail})
        logger.info("TASK %s step: %s %s", result.task_id, action, detail)

    # ==== MAIN ENTRY ====
    def execute_task(self, command: str, target_test: str = "",
                     max_iterations: int = MAX_ITERATIONS_DEFAULT) -> CodingResult:
        """Execute a programming command end-to-end with a bounded debug loop."""
        start = time.perf_counter()
        result = CodingResult(f"task_{uuid.uuid4().hex[:8]}", command)
        result.task_type = self.classify_task(command)
        exp = experience_tracker.start_task(result.task_type, command)
        regressions = 0

        try:
            # 1. Policy gate — reuses the existing autonomy enforcement.
            if self.policy is not None:
                risk = "SAFE" if result.task_type in ("explanation", "general") else "CONFIRMATION_REQUIRED"
                if not self.policy.validate_action(f"coding:{result.task_type}", risk):
                    result.summary = "Blocked by policy engine."
                    self._step(result, "policy_blocked", risk)
                    experience_tracker.complete_task(exp, "blocked")
                    return result
                self._step(result, "policy_ok", f"task_type={result.task_type} risk={risk}")

            if result.task_type == "explanation":
                return self._run_explanation(command, result, exp, start)

            # 2. Locate the target test (discover failing tests if not given).
            target = target_test or self._discover_failing_target(command, result)
            if not target:
                result.summary = "No failing test target located."
                experience_tracker.complete_task(exp, "no_target")
                return result
            self._step(result, "target_located", target)

            # 3. Bounded debugging loop — real execution, real failure capture.
            run = self.tester.run_single_test(target)
            self._step(result, "test_run", f"{target}: passed={run.passed} failed={run.failed}")

            for iteration in range(1, max_iterations + 1):
                result.iterations = iteration
                if run.success:
                    break

                failures = self.tester.parse_failures(run.stdout + run.stderr)
                if not failures:
                    failures = [{"test": target, "message": (run.stderr or run.stdout)[-500:]}]
                failure = failures[0]
                self._step(result, "failure_captured", failure["message"][:200])

                # 4. Root cause + minimal fix proposal.
                root_cause, patch = self._diagnose_and_propose(failure, result)
                result.root_cause = root_cause
                if not patch:
                    self._step(result, "no_patch_proposed", root_cause)
                    break

                # 5. Apply validated patch, remember it for rollback, re-run.
                rel_path, old_code, new_code = patch
                self._last_patch = (rel_path, old_code, new_code)
                patch_result = self.patcher.apply_patch(rel_path, old_code, new_code)
                if not patch_result.success:
                    self._step(result, "patch_rejected", patch_result.message)
                    break
                result.files_modified.append(rel_path)
                self._step(result, "patch_applied", rel_path)

                run = self.tester.run_single_test(target)
                self._step(result, "test_rerun",
                           f"iteration={iteration} passed={run.passed} failed={run.failed}")

            result.tests_passed = run.passed
            result.tests_failed = run.failed + run.errors

            # 6. Regression run — broader suite must not break.
            if run.success:
                self._step(result, "regression_started", "backend/tests")
                regression = self.tester.run_pytest("backend/tests")
                regressions = regression.failed + regression.errors
                result.tests_passed += regression.passed
                self._step(result, "regression_complete",
                           f"passed={regression.passed} failed={regression.failed} errors={regression.errors}")
                result.success = regressions == 0
                if regressions > 0 and getattr(self, "_last_patch", None):
                    rel_path, old_code, new_code = self._last_patch
                    self.patcher.apply_patch(rel_path, new_code, old_code)
                    result.files_modified = [f for f in result.files_modified if f != rel_path]
                    self._step(result, "regression_detected_patch_reverted", str(regressions))
            else:
                result.success = False

            # 7. Record structured experience + evidence-based capability metrics.
            result.duration_sec = time.perf_counter() - start
            outcome = "success" if result.success else "failed"
            exp.files_affected = list(result.files_modified)
            exp.tests_passed = result.tests_passed
            exp.tests_failed = result.tests_failed
            exp.iterations = result.iterations
            exp.duration_sec = result.duration_sec
            exp.strategy_used = "bounded-debug-loop"
            if result.root_cause:
                exp.errors_encountered.append(result.root_cause[:200])
            experience_tracker.complete_task(exp, outcome)

            regressions_introduced = regressions if not result.success and result.files_modified else 0
            capability_registry.record_task(
                skill=f"python_{result.task_type}",
                solved=result.success,
                tests_passed=result.tests_passed,
                tests_failed=result.tests_failed,
                iterations=max(result.iterations, 1),
                duration_sec=result.duration_sec,
                regressions=regressions_introduced,
            )

            result.summary = (
                f"{outcome.upper()}: iterations={result.iterations} "
                f"tests={result.tests_passed}p/{result.tests_failed}f "
                f"files={result.files_modified or 'none'}"
            )
            self._step(result, "complete", result.summary)
            return result

        except Exception as e:
            logger.error("TASK %s aborted: %s", result.task_id, e, exc_info=True)
            result.duration_sec = time.perf_counter() - start
            result.summary = f"Agent error: {e}"
            self._step(result, "agent_error", str(e)[:200])
            experience_tracker.complete_task(exp, "error")
            return result

    # ==== HELPERS ====
    def _run_explanation(self, command: str, result: CodingResult,
                         exp, start: float) -> CodingResult:
        """Explanation tasks are read-only: cognition answers from repo context."""
        self._step(result, "repo_inspection", "collecting project structure")
        structure = self.search.get_project_structure()
        context_head = str(structure)[:1500]

        if self.brain is not None:
            self._step(result, "cognition", "requesting explanation")
            try:
                answer = self.brain.think(
                    f"Explain for this repository (top-level structure:\n{context_head}\n\n"
                    f"Question: {command}"
                )
                result.summary = answer[:2000]
            except Exception as e:
                result.summary = f"Cognition failed: {e}"
                self._step(result, "cognition_error", str(e)[:200])
        else:
            result.summary = "Cognition unavailable; repository structure:\n" + context_head

        result.success = True
        result.duration_sec = time.perf_counter() - start
        experience_tracker.complete_task(exp, "success", persist=False)
        self._step(result, "complete", "explanation provided")
        return result

    def _discover_failing_target(self, command: str, result: CodingResult) -> str:
        """Run the backend suite and return the first failing test node id."""
        self._step(result, "repo_inspection", "discovering failing tests")
        run = self.tester.run_pytest("backend/tests")
        if run.success:
            return ""
        failures = self.tester.parse_failures(run.stdout + run.stderr)
        for f in failures:
            node = f.get("test", "")
            if node and "::" in node:
                return node
        return ""

    def _diagnose_and_propose(self, failure: Dict, result: CodingResult):
        """Diagnose a failure and obtain a minimal validated fix proposal.

        Returns (root_cause, (rel_path, old_code, new_code)) — patch is None
        when no fix could be proposed. All cognition routes through the
        existing AIBrain provider orchestration; without a brain no patch is
        fabricated (never fake success).
        """
        message = failure.get("message", "")
        self._step(result, "stack_trace_analysis", message[:200])

        # 1. Extract the first project source path from the traceback.
        root_str = str(self.repo.root)
        rel_path = ""
        for m in re.finditer(r'File "([^"]+)", line', message):
            path = m.group(1)
            if root_str in path:
                candidate = path.replace(root_str, "").lstrip("\\/").replace("\\", "/")
                if candidate.endswith(".py") and not candidate.startswith("backend/tests"):
                    rel_path = candidate
                    break
        if not rel_path:
            return ("Could not attribute failure to a project source file.", None)

        if not self.repo.file_exists(rel_path):
            return (f"Attributed file not found: {rel_path}", None)

        # 2. Read the suspect source for context.
        source = self.repo.read_file(rel_path)
        self._step(result, "code_understanding", f"{rel_path} ({len(source)} chars)")

        if self.brain is None:
            return ("Cognition unavailable — no patch will be fabricated.", None)

        # 3. Ask the existing brain (provider orchestration) for a minimal patch.
        prompt = (
            "You are ULTRON's programming agent. Diagnose the failing test and "
            "propose a MINIMAL fix.\n\n"
            f"Failing test: {failure.get('test', 'unknown')}\n"
            f"Failure message:\n{message[:1500]}\n\n"
            f"Source of {rel_path}:\n```python\n{source[:6000]}\n```\n\n"
            "Respond with EXACTLY this format and nothing else:\n"
            "ROOT_CAUSE: <one sentence>\n"
            "OLD:\n<exact lines from the source to replace>\n"
            "NEW:\n<corrected lines>\n"
        )
        try:
            response = self.brain.think(prompt)
        except Exception as e:
            return (f"Cognition error: {e}", None)

        root_cause, patch = self._parse_patch_response(response, rel_path)
        if patch is None:
            return (root_cause or "Cognition produced no parsable patch.", None)

        # 4. Validate the proposed code compiles before touching the repo.
        _, new_code, _ = patch
        valid, err = self.patcher.validate_python_syntax(new_code)
        if not valid:
            return (f"Proposed patch failed syntax validation: {err}", None)
        return (root_cause, patch)

    def _parse_patch_response(self, response: str, rel_path: str):
        """Parse a ROOT_CAUSE/OLD/NEW cognition response into a patch tuple."""
        rc_match = re.search(r"ROOT_CAUSE:\s*(.+)", response)
        root_cause = rc_match.group(1).strip() if rc_match else ""

        old_match = re.search(r"OLD:\s*\n(.*?)\nNEW:\s*\n(.*)", response, re.DOTALL)
        if not old_match:
            return (root_cause, None)
        old_code = old_match.group(1)
        new_code = old_match.group(2).strip()
        if not old_code.strip() or not new_code.strip() or old_code == new_code:
            return (root_cause, None)
        return (root_cause, (rel_path, old_code, new_code))

