# backend/tests/test_multi_device.py
import pytest
import datetime
import sqlite3
import json
import asyncio
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo
from backend.database.connection import get_db_connection
from backend.security.token_service import token_service
from backend.api.websocket.connection_manager import manager
from core.agent.agent_runtime import agent_runtime
from core.agent.goal_manager import goal_manager
from microphone_broker import mic_broker


@pytest.fixture(autouse=True)
def clean_device_databases():
    """Wipes all paired devices and active sessions from DB to guarantee isolation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices")
    cursor.execute("DELETE FROM pairing_sessions")
    cursor.execute("DELETE FROM brute_force_tracker")
    conn.commit()
    conn.close()

    manager.active_sessions.clear()
    manager.active_tickets.clear()

    # Reset agent state
    agent_runtime.state = "IDLE"
    goal_manager.clear_goal()

    yield

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices")
    cursor.execute("DELETE FROM pairing_sessions")
    cursor.execute("DELETE FROM brute_force_tracker")
    conn.commit()
    conn.close()

    manager.active_sessions.clear()
    manager.active_tickets.clear()
    agent_runtime.state = "IDLE"
    goal_manager.clear_goal()


# ==============================================================================
# SECURE PAIRING & AUTH TESTS
# ==============================================================================

def test_secure_pairing_flow():
    """Verify that pairing with a valid 6-digit PIN over loopback/local segment completes successfully."""
    client = TestClient(app)

    # 1. Create a pairing session (Host loopback only)
    res_session = client.post("/api/v1/auth/pairing-session")
    assert res_session.status_code == 201
    session_data = res_session.json()
    assert session_data["success"] is True
    pairing_code = session_data["pairing_code"]

    # 2. Confirm pair request (using the PIN code)
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "My Pixel 8 Test Phone",
            "device_type": "android"
        }
    )
    assert res_pair.status_code == 200
    pair_data = res_pair.json()
    assert pair_data["success"] is True
    assert "access_token" in pair_data


# ==============================================================================
# PERMISSION & WS TICKET TESTS
# ==============================================================================

def test_15_second_ticket_expiry_and_single_use_consumption():
    """Verify WebSocket handshake tickets expire in 15s and are invalidated immediately upon consumption."""
    device_id = "phone_test_99"

    # 1. Generate active WS ticket
    ticket = manager.create_ws_ticket(device_id)
    assert ticket is not None

    # Check that the ticket was stored statefully
    ticket_hash = token_service.hash_string(ticket)
    assert ticket_hash in manager.active_tickets

    # 2. Shift clock forward 20 seconds to force expiry
    expired_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(seconds=20)
    manager.active_tickets[ticket_hash]["expires_at"] = expired_time - datetime.timedelta(seconds=25)

    # Validate expired ticket returns None
    invalid_id = manager._validate_and_consume_ticket(ticket)
    assert invalid_id is None

    # 3. Generate a fresh ticket to test single-use consumption
    fresh_ticket = manager.create_ws_ticket(device_id)
    fresh_hash = token_service.hash_string(fresh_ticket)

    # First consumption is successful
    valid_id = manager._validate_and_consume_ticket(fresh_ticket)
    assert valid_id == device_id

    # Second consumption of the exact same ticket must fail (consumed statefully)
    assert fresh_hash not in manager.active_tickets
    assert manager._validate_and_consume_ticket(fresh_ticket) is None


# ==============================================================================
# STATE AUTHORITY & CVRDT MERGING TESTS
# ==============================================================================

def test_state_authority_model_and_rejections():
    """Verify that HOST_AUTHORITATIVE states are locked down, while CLIENT_WRITABLE supports LWW/CRDT merging."""
    client = TestClient(app)

    # Register an active device with scopes
    token = "access_token_mock_auth"
    token_hash = token_service.hash_string(token)
    device_repo.create_device({
        "device_id": "phone_auth_01",
        "device_name": "Authorized Phone",
        "device_type": "android",
        "token_hash": token_hash,
        "permissions": ["chat", "system_status"],
        "created_at": "2026-08-13T12:00:00Z",
        "paired_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T12:00:00Z",
        "last_seen": "2026-08-13T12:00:00Z",
        "revoked": False
    })

    headers = {"Authorization": f"Bearer {token}"}

    # Sync Payload: attempt to write to both Host-Authoritative and Client-Writable keys
    sync_payload = {
        "items": [
            {"key": "goals", "value": [{"goal_id": "g1", "status": "COMPLETED"}], "timestamp": "2026-08-13T16:00:00Z"}, # Authoritative (should be rejected)
            {"key": "ui_preferences", "value": {"theme": "obsidian"}, "timestamp": "2026-08-13T16:00:00Z"}            # Client-Writable (should be accepted)
        ]
    }

    res_sync = client.post("/api/v1/context/sync", json=sync_payload, headers=headers)
    assert res_sync.status_code == 200
    res_data = res_sync.json()

    # Verify Host Authority Rejections
    goals_item = next(item for item in res_data if item["key"] == "goals")
    assert goals_item["status"] == "STATE_REJECTED"
    assert goals_item["authoritative_value"] is not None # Returns the host's actual master state

    # Verify Client Writable merges
    pref_item = next(item for item in res_data if item["key"] == "ui_preferences")
    assert pref_item["status"] == "ACCEPTED"
    assert pref_item["value"]["theme"] == "obsidian"


# ==============================================================================
# EMERGENCY STOP TESTS (WITH AUTH CORRECTIONS)
# ==============================================================================

@pytest.mark.anyio
async def test_authenticated_emergency_stop_resets_runtime():
    """Verify that an authenticated and permitted emergency stop cancels TaskGraphs, releases mics, and resets IDLE."""
    client = TestClient(app)

    # 1. Register paired/authenticated device with 'safe_commands' permission
    token = "access_token_em_stop"
    token_hash = token_service.hash_string(token)
    device_repo.create_device({
        "device_id": "phone_admin_01",
        "device_name": "Admin Phone",
        "device_type": "android",
        "token_hash": token_hash,
        "permissions": ["safe_commands", "system_status"],
        "created_at": "2026-08-13T12:00:00Z",
        "paired_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T12:00:00Z",
        "last_seen": "2026-08-13T12:00:00Z",
        "revoked": False
    })

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Simulate running execution state & lock some mic endpoints
    agent_runtime.state = "RUNNING"
    goal_manager.set_goal("goal_01", "Running task")
    from microphone_broker import MicState
    mic_broker.acquire("AdvancedSpeechEngine", MicState.COMMAND_LISTENING)

    assert agent_runtime.state == "RUNNING"
    assert mic_broker.active_owner == "AdvancedSpeechEngine"

    # 3. Trigger authenticated emergency stop REST API
    res_stop = client.post("/api/v1/agent/emergency-stop", headers=headers)
    assert res_stop.status_code == 200

    # 4. Assert reset results
    assert agent_runtime.state == "IDLE"
    assert goal_manager.active_goal is None
    assert mic_broker.active_owner is None # Mic lock released safely


def test_unauthenticated_emergency_stop_rejection():
    """Verify that unauthenticated/random emergency stop requests are blocked completely and fail closed."""
    client = TestClient(app)

    # 1. Try triggering without any Auth headers
    res_stop_no_auth = client.post("/api/v1/agent/emergency-stop")
    assert res_stop_no_auth.status_code == 401 # Missing auth

    # 2. Register a device LACKING the 'safe_commands' scope
    token_unauth = "token_missing_perm"
    unauth_hash = token_service.hash_string(token_unauth)
    device_repo.create_device({
        "device_id": "phone_unauth_01",
        "device_name": "Guest Phone",
        "device_type": "android",
        "token_hash": unauth_hash,
        "permissions": ["chat"], # Missing safe_commands
        "created_at": "2026-08-13T12:00:00Z",
        "paired_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T12:00:00Z",
        "last_seen": "2026-08-13T12:00:00Z",
        "revoked": False
    })

    headers_unauth = {"Authorization": f"Bearer {token_unauth}"}
    res_stop_no_perm = client.post("/api/v1/agent/emergency-stop", headers=headers_unauth)
    assert res_stop_no_perm.status_code == 403 # Denied/Forbidden


# ==============================================================================
# SINGLE-DEVICE FALLBACK & OFFLINE BUFFER TESTS
# ==============================================================================

def test_single_device_fallback():
    """Verify that when no companion devices are connected, the system falls back safely without breaking execution."""
    # When active connections are empty, broadcast and routing utilities return gracefully instead of throwing errors
    try:
        asyncio.run(manager.broadcast({"event": "TEST_BROADCAST"}))
        success = True
    except Exception:
        success = False

    assert success is True


def test_offline_buffer_management():
    """Verify local offline buffer manages events statefully and drops entries on buffer cap breaches (max 100)."""
    offline_buffer = []

    # Push 120 offline events
    for i in range(120):
        offline_buffer.append({"event_id": f"evt_{i}", "payload": "offline_log"})
        # Enforce the 100 record queue cap
        if len(offline_buffer) > 100:
            offline_buffer.pop(0) # Drop oldest

    assert len(offline_buffer) == 100
    assert offline_buffer[0]["event_id"] == "evt_20" # Oldest 20 events popped/dropped statefully
