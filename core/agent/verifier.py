"""Verification primitives for autonomous task execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    message: str
    value: Any = None


class Verifier:
    """Verify outputs without assuming that execution implies success."""

    def __init__(self, checks: Optional[list[Callable[[Any], bool]]] = None) -> None:
        self.checks = checks or []

    def verify(self, value: Any) -> VerificationResult:
        for check in self.checks:
            try:
                if not check(value):
                    return VerificationResult(False, "A verification check failed.", value)
            except Exception as exc:
                return VerificationResult(False, f"Verification error: {exc}", value)
        return VerificationResult(True, "Verification passed.", value)
