# adaptive_programming/__init__.py
"""
Adaptive Programming Engine V1 — programming intelligence + controlled self-improvement.

Sits ON TOP of the existing ULTRON architecture:
  - Reuses AIBrain for cognition
  - Reuses Planner for task decomposition
  - Reuse ToolOrchestrator/ToolRegistry for execution
  - Reuses PolicyEngine for autonomy/risk enforcement
  - Reuses memory_manager for experience storage
  - Reuses the evolution engine (hypothesis → experiment → evaluate → policy → update)
  - Reuse update_manager + rollback_manager for versioned deployment

This package adds programming-specific capabilities:
  - Repository inspection and code search
  - Patch application with syntax validation
  - Iterative debugging loop
  - Test execution and regression detection
  - Evidence-based capability tracking
  - Programming benchmarks with executable verification
  - Improvement proposals fed into the existing evolution pipeline
"""

from adaptive_programming.coding_agent import CodingAgent, CodingResult
from adaptive_programming.capability_registry import capability_registry
from adaptive_programming.experience_tracker import experience_tracker
from adaptive_programming.programming_benchmark import benchmark_suite

__all__ = [
    "CodingAgent",
    "CodingResult",
    "capability_registry",
    "experience_tracker",
    "benchmark_suite",
]
