# backend/tests/test_phase2.py
import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_lockouts():
    """Ensure that brute force lockouts are cleared before testing."""
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")
    yield
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")


@pytest.fixture(scope="module")
def auth_headers():
    """Generates a valid paired client token and returns authorization headers."""
    # Ensure fresh state on module load
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")

    # 1. Create session PIN
    session_response = client.post("/api/v1/auth/pairing-session")
    sess_data = session_response.json()
    pairing_pin = sess_data["pairing_code"]

    # 2. Pair device
    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Phase 2 Test Device",
        "device_type": "android"
    })
    token = pair_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# CHAT API TESTS
# ==============================================================================

def test_chat_valid_payload(auth_headers):
    """Verify that POST /api/v1/chat returns a valid 200 response matching the schema."""
    response = client.post("/api/v1/chat", headers=auth_headers, json={"message": "Say hello in one short sentence"})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0
    assert "conversation_id" in data
    assert "timestamp" in data


def test_chat_empty_message_rejected(auth_headers):
    """Verify that blank or empty messages are correctly rejected with 422 validation errors."""
    response = client.post("/api/v1/chat", headers=auth_headers, json={"message": ""})
    assert response.status_code == 422

    response = client.post("/api/v1/chat", headers=auth_headers, json={"message": "   "})
    assert response.status_code == 422


def test_chat_oversized_message_rejected(auth_headers):
    """Verify that extremely oversized messages are rejected with 422 validation errors."""
    response = client.post("/api/v1/chat", headers=auth_headers, json={"message": "A" * 2001})
    assert response.status_code == 422


# ==============================================================================
# SYSTEM TELEMETRY TESTS
# ==============================================================================

def test_system_telemetry_endpoint(auth_headers):
    """Verify that GET /api/v1/system/status returns active hardware metrics."""
    response = client.get("/api/v1/system/status", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "cpu" in data
    assert "usage_percent" in data["cpu"]

    assert "memory" in data
    assert "usage_percent" in data["memory"]
    assert "used_mb" in data["memory"]
    assert "total_mb" in data["memory"]

    assert "disk" in data
    assert "usage_percent" in data["disk"]

    assert "battery" in data
    assert "available" in data["battery"]
    assert "percent" in data["battery"]

    assert "gpu" in data
    assert "available" in data["gpu"]
    assert "name" in data["gpu"]

    assert "os" in data
    assert "name" in data["os"]
    assert "version" in data["os"]


# ==============================================================================
# COMMAND DISPATCH AND SECURITY GATEWAY TESTS
# ==============================================================================

def test_command_valid_safe_execution(auth_headers):
    """Verify that an allowlisted SAFE command successfully runs and generates metadata."""
    response = client.post("/api/v1/commands", headers=auth_headers, json={"command": "get_time", "parameters": {}})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "command_id" in data
    assert data["command_id"].startswith("cmd_")
    assert data["status"] == "completed"
    assert "result" in data


def test_command_unknown_rejected(auth_headers):
    """Verify that requests for unlisted commands are rejected with 400 Bad Request."""
    response = client.post("/api/v1/commands", headers=auth_headers, json={"command": "format_disk_now", "parameters": {}})
    assert response.status_code == 400

    data = response.json()
    assert data["success"] is False
    assert data["status"] == "rejected"
    assert data["error"]["code"] == "COMMAND_NOT_ALLOWED"


def test_command_high_risk_blocked_in_phase2(auth_headers):
    """Verify that HIGH_RISK commands are securely intercepted and blocked with 403 Forbidden."""
    response = client.post("/api/v1/commands", headers=auth_headers, json={"command": "shutdown", "parameters": {}})
    assert response.status_code == 403

    data = response.json()
    assert data["success"] is False
    assert data["status"] == "rejected"
    assert data["error"]["code"] == "HIGH_RISK_COMMAND_REQUIRES_AUTHORIZATION"


def test_command_arbitrary_shell_interpreters_blocked(auth_headers):
    """Verify that raw Python/PowerShell/Shell commands trigger Pydantic validation failures."""
    payloads = [
        {"command": "python", "parameters": {}},
        {"command": "powershell", "parameters": {}},
        {"command": "os.system", "parameters": {"cmd": "whoami"}},
        {"command": "sh", "parameters": {}},
        {"command": "cmd.exe", "parameters": {}},
    ]

    for payload in payloads:
        response = client.post("/api/v1/commands", headers=auth_headers, json=payload)
        assert response.status_code == 422
