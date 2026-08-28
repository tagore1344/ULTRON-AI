# backend/tests/test_hardening.py — Async subprocess hardening & power-command dispatch
import asyncio
import pytest

from core.tools.tool_registry import ToolRegistry
from backend.services.command_service import command_service


class FakeSystem:
    """Records calls without touching real OS hardware."""

    def __init__(self):
        self.calls = []

    def shutdown(self):
        self.calls.append("shutdown")

    def restart(self):
        self.calls.append("restart")

    def sleep(self):
        self.calls.append("sleep")

    def lock_screen(self):
        self.calls.append("lock_screen")

    def cancel_shutdown(self):
        self.calls.append("cancel_shutdown")

    def open_website(self, url):
        self.calls.append(("open_website", url))


class FakeApps:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def open_app(self, name):
        self.calls.append(name)
        return self.result


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.system = FakeSystem()
    reg.apps = FakeApps()
    return reg


# ==============================================================================
# POWER COMMAND DISPATCH (previously "Unknown tool intent")
# ==============================================================================

@pytest.mark.anyio
async def test_power_command_dispatch(registry):
    """HIGH_RISK power commands must reach the controller, not fall through."""
    for intent, expected in [
        ("system.shutdown", "shutdown"),
        ("system.restart", "restart"),
        ("system.sleep", "sleep"),
        ("system.lock_screen", "lock_screen"),
        ("system.cancel_shutdown", "cancel_shutdown"),
    ]:
        result = await registry.execute({"intent": intent, "target": ""})
        assert expected in registry.system.calls, f"{intent} was not dispatched"
        assert "initiated" in result.lower() or "locked" in result.lower() or "cancelled" in result.lower()


@pytest.mark.anyio
async def test_app_open_async_dispatch(registry):
    """app.open routes through the app controller and reports success."""
    result = await registry.execute({"intent": "app.open", "target": "chrome"})
    assert registry.apps.calls == ["chrome"]
    assert "Successfully opened chrome" in result


@pytest.mark.anyio
async def test_app_open_website_async_dispatch(registry):
    """Website shortcuts use the system controller's async open_website path."""
    result = await registry.execute({"intent": "app.open", "target": "youtube"})
    assert ("open_website", "www.youtube.com") in registry.system.calls
    assert "Opened youtube" in result


# ==============================================================================
# COMMAND SERVICE MAPPING (closes the allowlist->intent gap)
# ==============================================================================

def test_power_commands_map_to_intents():
    assert command_service._map_to_intent_data("shutdown", {}) == ("system.shutdown", "")
    assert command_service._map_to_intent_data("restart", {}) == ("system.restart", "")
    assert command_service._map_to_intent_data("sleep", {}) == ("system.sleep", "")
    assert command_service._map_to_intent_data("lock_screen", {}) == ("system.lock_screen", "")
    assert command_service._map_to_intent_data("cancel_shutdown", {}) == ("system.cancel_shutdown", "")


def test_existing_command_mapping_preserved():
    assert command_service._map_to_intent_data("get_time", {}) == ("system.time", "")
    assert command_service._map_to_intent_data("launch_application", {"application": "chrome"}) == ("app.open", "chrome")
    assert command_service._map_to_intent_data("open_website", {"url": "example.com"}) == ("app.open", "example.com")
    assert command_service._map_to_intent_data("unknown_cmd", {}) == ("chat", "")


# ==============================================================================
# ASYNC VARIANT PRESENCE (backward-compatible sync methods retained)
# ==============================================================================

def test_system_controller_async_variants_exist():
    from system_controller import SystemController
    for name in ("ashutdown", "arestart", "asleep", "alock_screen", "acancel_shutdown"):
        assert hasattr(SystemController, name), f"missing async variant {name}"
        assert asyncio.iscoroutinefunction(getattr(SystemController, name))
    # Sync methods preserved for the legacy desktop loop
    for name in ("shutdown", "restart", "sleep", "lock_screen", "cancel_shutdown"):
        assert hasattr(SystemController, name)


def test_app_controller_async_variant_exists():
    from app_controller import AppController
    assert hasattr(AppController, "aopen_app")
    assert asyncio.iscoroutinefunction(AppController.aopen_app)
    assert hasattr(AppController, "open_app")  # sync path preserved


# ==============================================================================
# END-TO-END: allowlisted HIGH_RISK command reaches the controller
# ==============================================================================

@pytest.mark.anyio
async def test_high_risk_allowlisted_command_executes_after_approval(registry, monkeypatch):
    """Simulates the post-confirmation execution a mobile client triggers today.

    Previously the allowlisted HIGH_RISK command mapped to intent "chat" and
    fell through as 'Unknown tool intent'; now it reaches the controller.
    """
    intent, target = command_service._map_to_intent_data("shutdown", {})
    assert intent == "system.shutdown"
    result = await registry.execute({"intent": intent, "target": target})
    assert "shutdown" in registry.system.calls
    assert "Shutdown initiated" in result
