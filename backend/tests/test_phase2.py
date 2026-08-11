# backend/tests/test_phase2.py
import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.services.command_service import command_service

client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# CHAT API TESTS
# ==============================================================================

def test_chat_valid_payload():
    """Verify that POST /api/v1/chat returns a valid 200 response matching the schema."""
    response = client.post("/api/v1/chat", json={"message": "Say hello in one short sentence"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0
    assert "conversation_id" in data
    assert "timestamp" in data


def test_chat_empty_message_rejected():
    """Verify that blank or empty messages are correctly rejected with 422 validation errors."""
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422

    response = client.post("/api/v1/chat", json={"message": "   "})
    assert response.status_code == 422


def test_chat_oversized_message_rejected():
    """Verify that extremely oversized messages are rejected with 422 validation errors."""
    response = client.post("/api/v1/chat", json={"message": "A" * 2001})
    assert response.status_code == 422


# ==============================================================================
# SYSTEM TELEMETRY TESTS
# ==============================================================================

def test_system_telemetry_endpoint():
    """Verify that GET /api/v1/system/status returns active hardware metrics."""
    response = client.get("/api/v1/system/status")
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

def test_command_valid_safe_execution():
    """Verify that an allowlisted SAFE command successfully runs and generates metadata."""
    response = client.post("/api/v1/commands", json={"command": "get_time", "parameters": {}})
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "command_id" in data
    assert data["command_id"].startswith("cmd_")
    assert data["status"] == "completed"
    assert "result" in data


def test_command_unknown_rejected():
    """Verify that requests for unlisted commands are rejected with 400 Bad Request."""
    response = client.post("/api/v1/commands", json={"command": "format_disk_now", "parameters": {}})
    assert response.status_code == 400
    
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "rejected"
    assert data["error"]["code"] == "COMMAND_NOT_ALLOWED"


def test_command_high_risk_blocked_in_phase2():
    """Verify that HIGH_RISK commands are securely intercepted and blocked with 403 Forbidden."""
    response = client.post("/api/v1/commands", json={"command": "shutdown", "parameters": {}})
    assert response.status_code == 403
    
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "rejected"
    assert data["error"]["code"] == "HIGH_RISK_COMMAND_REQUIRES_AUTHORIZATION"


def test_command_arbitrary_shell_interpreters_blocked():
    """Verify that raw Python/PowerShell/Shell commands trigger Pydantic validation failures."""
    payloads = [
        {"command": "python", "parameters": {}},
        {"command": "powershell", "parameters": {}},
        {"command": "os.system", "parameters": {"cmd": "whoami"}},
        {"command": "sh", "parameters": {}},
        {"command": "cmd.exe", "parameters": {}},
    ]
    
    for payload in payloads:
        response = client.post("/api/v1/commands", json=payload)
        assert response.status_code == 422
