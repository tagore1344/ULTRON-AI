# test_app_controller.py
import time
from unittest.mock import MagicMock, patch
import subprocess

from app_controller import AppController


class MockSpeechEngine:
    def speak(self, text):
        pass


def test_app_controller_smoke():
    speech = MockSpeechEngine()
    app_controller = AppController(speech)

    # Legitimate allowlisted commands
    with patch("subprocess.Popen") as mock_popen:
        app_controller.open_app("notepad")
        # notepad is matched in win_commands (notepad.exe)
        mock_popen.assert_called_with(["notepad.exe"])

    with patch("subprocess.Popen") as mock_popen:
        app_controller.open_app("calc")
        # calc is matched in win_commands (calc.exe)
        mock_popen.assert_called_with(["calc.exe"])


def test_app_controller_security_boundaries():
    """Verify that AppController.open_app strictly rejects arbitrary paths, shell commands, or interpreters."""
    speech = MockSpeechEngine()
    app_controller = AppController(speech)

    dangerous_payloads = [
        "powershell",
        "cmd",
        "python",
        "python.exe",
        "powershell.exe",
        "cmd.exe",
        "evil.exe",
        "C:\\malicious.exe",
        "../../malicious.exe",
        "evil & whoami",
        "evil | whoami",
        "evil; whoami",
        "evil > output.txt"
    ]

    with patch("subprocess.Popen") as mock_popen, \
         patch("subprocess.run") as mock_run, \
         patch("os.startfile", create=True) as mock_startfile:

        for payload in dangerous_payloads:
            result = app_controller.open_app(payload)
            # Rejects either via sanitization or by failing all explicit allowlist dicts
            assert result is False

            # Ensure NO process or shell executions are triggered with the payload
            mock_popen.assert_not_called()
            mock_run.assert_not_called()
            mock_startfile.assert_not_called()


@patch("webbrowser.open")
def test_app_controller_chrome_and_social_mappings(mock_web_open):
    """Verify that chrome, whatsapp, youtube, and instagram map correctly."""
    from core.tools.tool_registry import ToolRegistry

    # We instantiate ToolRegistry which leverages our updated launch mappings
    registry = ToolRegistry()

    # Mock systems to avoid dependencies
    registry.system = MagicMock()
    registry.apps = MagicMock()

    # Test safe social media triggers (Direct web shortcut bypasses apps)
    registry.apps.open_app.return_value = False

    import asyncio

    async def run_test():
        # Test youtube (Direct web shortcut bypasses apps)
        await registry.execute({"intent": "app.open", "target": "youtube"})
        registry.system.open_website.assert_called_with("www.youtube.com")

        # Test instagram
        await registry.execute({"intent": "app.open", "target": "instagram"})
        registry.system.open_website.assert_called_with("www.instagram.com")

        # Test Chrome (native launcher triggered)
        await registry.execute({"intent": "app.open", "target": "chrome"})
        registry.apps.open_app.assert_called_with("chrome")

        # Test Typo "chroome" (maps safely to chrome alias)
        await registry.execute({"intent": "app.open", "target": "chroome"})
        registry.apps.open_app.assert_called_with("chrome")

    asyncio.run(run_test())


def test_command_parsing_decomposition_and_whatsapp_confirmation():
    """Verify that composite voice triggers decompose cleanly and require explicit message confirmation."""
    from core.intent.intent_router import IntentRouter
    from core.tools.tool_registry import ToolRegistry

    router = IntentRouter()
    registry = ToolRegistry()

    # Mock components
    registry.system = MagicMock()
    registry.apps = MagicMock()

    # 1. Test standard "open whatsapp" routes normally
    res_single = router.detect("open whatsapp")
    assert res_single["intent"] == "app.open"
    assert res_single["target"] == "whatsapp"

    # 2. Test composite "open whatsapp and send a message to chethan jnu as hi"
    res_composite = router.detect("open whatsapp and send a message to chethan jnu as hi")
    assert res_composite["intent"] == "composite"
    assert len(res_composite["actions"]) == 2

    action_1 = res_composite["actions"][0]
    assert action_1["intent"] == "app.open"
    assert action_1["target"] == "whatsapp"

    action_2 = res_composite["actions"][1]
    assert action_2["intent"] == "app.send_message"
    assert action_2["recipient"] == "chethan jnu"
    assert action_2["message"] == "hi"
    assert action_2["app"] == "whatsapp"

    # 3. Test open chroome maps safely to chrome
    res_typo = router.detect("open chroome")
    assert res_typo["intent"] == "app.open"
    assert res_typo["target"] == "chroome" # Captured as is, mapped safely inside ToolRegistry!

    # 4. Test open chromeeeeeeee (Does NOT match any hardcoded allowlist mappings)
    res_unsupported = router.detect("open chromeeeeeeee")
    assert res_unsupported["intent"] == "app.open"

    import asyncio

    async def run_test():
        # ToolRegistry execute on chromeeeeeeee returns False/not found
        registry.apps.open_app.return_value = False
        exec_res = await registry.execute(res_unsupported)
        assert "not found" in exec_res

        # 5. Test malicious multi-action string blocks arbitrary commands
        malicious_prompt = "open whatsapp and send a message to evil as whoami"
        res_malicious = router.detect(malicious_prompt)
        assert res_malicious["intent"] == "composite"

        malicious_action_2 = res_malicious["actions"][1]
        assert malicious_action_2["message"] == "whoami" # Completely inert text payload

        # Executes safely with zero process invocations
        exec_malicious_res = await registry.execute(res_malicious)
        assert "WhatsApp message prepared for confirmation" in exec_malicious_res

        # 6. Test message confirmation behavior
        # Trigger send_message directly and verify it returns the mandatory confirmation message
        send_msg_res = await registry.execute(action_2)
        assert send_msg_res == "WhatsApp message prepared for confirmation, but sending is not yet supported."

    asyncio.run(run_test())
