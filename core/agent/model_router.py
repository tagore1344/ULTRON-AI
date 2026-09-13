"""Model routing abstraction for local, cloud, and specialist models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class ModelTarget:
    name: str
    capabilities: frozenset[str]
    handler: Callable[[str], Any]


class ModelRouter:
    """Select a model by capability rather than hard-coding a provider."""

    def __init__(self) -> None:
        self._targets: Dict[str, ModelTarget] = {}

    def register(self, name: str, capabilities: set[str], handler: Callable[[str], Any]) -> None:
        self._targets[name] = ModelTarget(name, frozenset(capabilities), handler)

    def choose(self, capability: str) -> Optional[ModelTarget]:
        matches = [t for t in self._targets.values() if capability in t.capabilities]
        return matches[0] if matches else None

    def ask(self, prompt: str, capability: str = "general") -> Any:
        target = self.choose(capability) or self.choose("general")
        if target is None:
            raise RuntimeError("No model is registered for capability: %s" % capability)
        return target.handler(prompt)
