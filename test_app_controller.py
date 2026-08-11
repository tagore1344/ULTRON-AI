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
