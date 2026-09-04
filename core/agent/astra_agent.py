"""Astra-class agent kernel for ULTRON.

Uses the OpenAI Responses API as the reasoning engine and gives it a small,
observable local workspace tool surface for autonomous software work.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


class AstraAgent:
    """Run bounded, tool-using tasks against a local project workspace."""

    def __init__(self, workspace: str | None = None, max_turns: int = 24) -> None:
        self.workspace = Path(workspace or os.getenv("ULTRON_WORKSPACE", os.getcwd())).resolve()
        self.max_turns = max(1, int(max_turns))
        self.model = os.getenv("ULTRON_MODEL", "gpt-6-astra")
        self.client = None
        if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def available(self) -> bool:
        return self.client is not None

    def _safe_path(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValueError("Path escapes the ULTRON workspace.")
        return candidate

    def _run_shell(self, command: str, timeout: int = 30) -> dict[str, Any]:
        """Run a command inside the configured workspace with a hard timeout."""
        result = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=max(1, min(int(timeout), 120)),
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }

    def _call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "workspace_list":
            path = self._safe_path(args.get("path", "."))
            if not path.is_dir():
                raise ValueError("Not a directory: " + str(args.get("path", ".")))
            entries = []
            for item in sorted(path.iterdir(), key=lambda p: p.name.lower())[:500]:
                entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file"})
            return {"path": str(path.relative_to(self.workspace)), "entries": entries}

        if name == "workspace_read":
            path = self._safe_path(args["path"])
            if not path.is_file():
                raise ValueError("Not a file: " + args["path"])
            limit = max(1, min(int(args.get("max_chars", 30000)), 100000))
            return {"path": args["path"], "content": path.read_text(encoding="utf-8")[:limit]}

        if name == "workspace_write":
            path = self._safe_path(args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args.get("content", ""), encoding="utf-8")
            return {"path": args["path"], "written": True, "bytes": path.stat().st_size}

        if name == "workspace_shell":
            return self._run_shell(args["command"], args.get("timeout", 30))

        if name == "git_status":
            return self._run_shell("git status --short && git branch --show-current")

        if name == "git_diff":
            return self._run_shell("git diff --stat && git diff -- . ':(exclude)*.lock'", 60)

        if name == "git_commit":
            message = args["message"].strip()
            if not message:
                raise ValueError("Commit message cannot be empty.")
            return self._run_shell("git add -A && git commit -m " + json.dumps(message), 60)

        raise ValueError("Unknown Astra tool: " + name)

    @staticmethod
    def _tools() -> list[dict[str, Any]]:
        return [
            {"type": "web_search"},
            {"type": "function", "name": "workspace_list", "description": "List files in the project workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}},
            {"type": "function", "name": "workspace_read", "description": "Read a UTF-8 text file from the project workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}}, "required": ["path"]}},
            {"type": "function", "name": "workspace_write", "description": "Create or replace a UTF-8 text file in the project workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"type": "function", "name": "workspace_shell", "description": "Run a shell command inside the project workspace. Use for tests, builds, linters, and diagnostics.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}},
            {"type": "function", "name": "git_status", "description": "Inspect git status and current branch.", "parameters": {"type": "object", "properties": {}, "required": []}},
            {"type": "function", "name": "git_diff", "description": "Inspect the current git diff.", "parameters": {"type": "object", "properties": {}, "required": []}},
            {"type": "function", "name": "git_commit", "description": "Commit completed workspace changes. Do not push or publish changes.", "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}},
        ]

    def run(self, goal: str) -> str:
        if not self.available():
            return "Astra agent unavailable: set OPENAI_API_KEY and install the OpenAI SDK."

        instructions = (
            "You are ULTRON's autonomous software agent. Work toward the user's goal "
            "using the available tools. Inspect before editing. Make the smallest correct "
            "changes, run relevant tests after changes, diagnose failures, and iterate. "
            "Never claim success without verification. Stay inside the workspace. "
            "Do not push to remote repositories. Summarize changes and verification at the end."
        )
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": os.getenv("ULTRON_REASONING_EFFORT", "high")},
            instructions=instructions,
            input=goal,
            tools=self._tools(),
        )

        for _ in range(self.max_turns):
            calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not calls:
                return response.output_text or "Astra completed without a textual summary."

            tool_outputs = []
            for call in calls:
                try:
                    args = json.loads(call.arguments or "{}")
                    result = self._call_tool(call.name, args)
                except Exception as exc:
                    result = {"error": str(exc)}
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })

            response = self.client.responses.create(
                model=self.model,
                reasoning={"effort": os.getenv("ULTRON_REASONING_EFFORT", "high")},
                instructions=instructions,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=self._tools(),
            )

        return "Astra stopped after reaching the maximum tool-turn limit without verified completion."
