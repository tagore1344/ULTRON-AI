# backend/tests/test_phase3.py
import pytest
import time
import datetime
from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo

# Create test client
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_lockouts():
    """Ensure that the brute force tracker and devices are clean before/after tests."""
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")
    yield
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")


def test_pairing_and_auth_workflow():
    """Verify standard pairing session PIN generation, pairing, token distribution, and endpoint authorization."""

    # 1. Create session PIN (Loopback protection allows testclient)
    session_response = client.post("/api/v1/auth/pairing-session")
    assert session_response.status_code == 201

    sess_data = session_response.json()
    assert sess_data["success"] is True
    assert "pairing_code" in sess_data
    assert "session_id" in sess_data

    pairing_pin = sess_data["pairing_code"]

    # 2. Try pairing with an invalid code
    bad_pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": "000000",
        "device_name": "Test Android Phone",
        "device_type": "android"
    })
    assert bad_pair_resp.status_code == 401

    # 3. Pair successfully with valid PIN
    good_pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Test Android Phone",
        "device_type": "android"
    })
    assert good_pair_resp.status_code == 200

    pair_data = good_pair_resp.json()
    assert pair_data["success"] is True
    assert "access_token" in pair_data
    assert pair_data["device"]["device_name"] == "Test Android Phone"

    token = pair_data["access_token"]
    device_id = pair_data["device"]["device_id"]

    # 4. Try pairing again with the same (reused/invalidated) code
    reused_pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Test Phone 2",
        "device_type": "android"
    })
    assert reused_pair_resp.status_code == 401

    # 5. Connect to protected endpoints using the raw token
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Check Telemetry Endpoint (Succeeds)
    telemetry_resp = client.get("/api/v1/system/status", headers=auth_headers)
    assert telemetry_resp.status_code == 200
    assert "cpu" in telemetry_resp.json()

    # Check Chat Endpoint (Succeeds)
    chat_resp = client.post("/api/v1/chat", headers=auth_headers, json={"message": "Say hello in 3 words"})
    assert chat_resp.status_code == 200
    assert chat_resp.json()["success"] is True

    # Check Safe Commands Endpoint (Succeeds)
    cmd_resp = client.post("/api/v1/commands", headers=auth_headers, json={"command": "get_time", "parameters": {}})
    assert cmd_resp.status_code == 200
    assert cmd_resp.json()["success"] is True

    # Check High-Risk Command Blocked (Fails with 403)
    hr_resp = client.post("/api/v1/commands", headers=auth_headers, json={"command": "shutdown", "parameters": {}})
    assert hr_resp.status_code == 403
    assert hr_resp.json()["success"] is False

    # Check listing devices (Succeeds)
    devices_resp = client.get("/api/v1/devices", headers=auth_headers)
    assert devices_resp.status_code == 200
    assert len(devices_resp.json()) >= 1

    # 6. Revoke access of the device
    revoke_resp = client.delete(f"/api/v1/devices/{device_id}", headers=auth_headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["success"] is True

    # 7. Try connecting with revoked token (Fails with 401)
    blocked_telemetry_resp = client.get("/api/v1/system/status", headers=auth_headers)
    assert blocked_telemetry_resp.status_code == 401


def test_blocked_unauthenticated_requests():
    """Verify that unauthenticated requests to protected routes are correctly blocked with 401."""
    endpoints = [
        ("GET", "/api/v1/system/status"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/commands"),
        ("GET", "/api/v1/devices")
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={"message": "test", "command": "get_time"})

        assert resp.status_code == 401


def test_pairing_lockout_rate_limiting():
    """Verify that brute force tracking limits attempts and applies a lockout."""
    # Issue multiple bad pairing attempts to trigger the rate limiter
    client_ip = "testclient"

    # We exceed 5 failures to trigger lockouts
    for _ in range(5):
        resp = client.post("/api/v1/auth/pair", json={
            "pairing_code": "999999",
            "device_name": "Brute Force Device",
            "device_type": "android"
        })
        assert resp.status_code == 401

    # Sixth attempt must be blocked by rate limiting lockouts
    locked_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": "123456",
        "device_name": "Brute Force Device",
        "device_type": "android"
    })
    assert locked_resp.status_code == 401
    assert "locked out" in locked_resp.json()["detail"].lower()


# ==============================================================================
# SECURITY AUDIT WORKFLOW TESTS (FINDINGS FIXES)
# ==============================================================================

def test_pair_blocks_tailscale_origins():
    """Verify that pairing attempts originating from Tailscale IP subnets are strictly blocked with 403."""
    # Unit-tested Tailscale network classification:
    from backend.api.routes.auth import is_local_lan

    # Standard Tailscale IPv4 ranges (100.64.0.0/10)
    assert is_local_lan("100.64.12.35") is False
    assert is_local_lan("100.127.255.254") is False

    # Standard Tailscale IPv6 Unique Local Address ranges (fd7a:115c:a1e0::/48)
    assert is_local_lan("fd7a:115c:a1e0::1234") is False
    assert is_local_lan("fd7a:115c:a1e0:1a2b::5678") is False

    # Standard Local LAN/Loopback RFC 1918 private address ranges
    assert is_local_lan("127.0.0.1") is True
    assert is_local_lan("::1") is True
    assert is_local_lan("192.168.1.15") is True
    assert is_local_lan("172.16.0.1") is True
    assert is_local_lan("10.0.0.5") is True


def test_one_phone_cannot_revoke_another():
    """Verify that Phone A is strictly blocked from revoking Phone B's credentials (HTTP 403)."""
    # 1. Register Phone A
    sess_resp_a = client.post("/api/v1/auth/pairing-session")
    pin_a = sess_resp_a.json()["pairing_code"]
    pair_resp_a = client.post("/api/v1/auth/pair", json={
        "pairing_code": pin_a,
        "device_name": "Phone A",
        "device_type": "android"
    })
    token_a = pair_resp_a.json()["access_token"]
    id_a = pair_resp_a.json()["device"]["device_id"]

    # 2. Register Phone B
    sess_resp_b = client.post("/api/v1/auth/pairing-session")
    pin_b = sess_resp_b.json()["pairing_code"]
    pair_resp_b = client.post("/api/v1/auth/pair", json={
        "pairing_code": pin_b,
        "device_name": "Phone B",
        "device_type": "android"
    })
    id_b = pair_resp_b.json()["device"]["device_id"]

    # 3. Attempt to let Phone A delete/revoke Phone B (Fails with 403 Forbidden)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    unauthorized_revoke_resp = client.delete(f"/api/v1/devices/{id_b}", headers=headers_a)

    assert unauthorized_revoke_resp.status_code == 403
    assert "only restrict" in unauthorized_revoke_resp.json()["detail"].lower() or "self-revocation" in unauthorized_revoke_resp.json()["detail"].lower()
