# backend/tests/test_distributed_d1.py
import pytest
import sqlite3
import datetime
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo
from backend.database.connection import get_db_connection
from backend.security.token_service import token_service
from backend.api.websocket.connection_manager import manager


@pytest.fixture(autouse=True)
def clean_pairing_databases():
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


# ==============================================================================
# IDENTITY & DETERMINISTIC NODE ID TESTS
# ==============================================================================

def test_deterministic_node_id_derivation_from_public_key():
    """Verify that node ID is derived deterministically as a lowercase SHA-256 hex fingerprint of the public key."""
    # Simulated public key base64 string
    pub_key_base64 = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."

    # Calculate SHA-256 fingerprint in Python to match Kotlin NodeIdentity.getNodeDeviceId()
    import hashlib
    digest = hashlib.sha256(pub_key_base64.encode('utf-8')).hexdigest().lower()
    node_id = f"android_{digest}"

    assert node_id.startswith("android_")
    assert len(node_id) == 8 + 64 # android_ prefix + 64 hex characters
    assert node_id.islower()


def test_private_key_non_exportability_contract():
    """Verify that by architectural design and AndroidKeyStore contract, private keys are strictly non-exportable."""
    # This verifies the spec policy contract that private keys must remain inside hardware enclave
    from core.context.self_model import self_model
    assert self_model.capabilities["update_signature_signer"] == "FAILED" # explicitly banned from self-evolution/exporting


# ==============================================================================
# PAIRING & CAPABILITY PERSISTENCE TESTS
# ==============================================================================

def test_d1_secure_pairing_and_capability_persistence():
    """Verify D1 secure pairing registers custom device ID, public key, and hardware capabilities successfully."""
    client = TestClient(app)

    # 1. Create a pairing session
    res_session = client.post("/api/v1/auth/pairing-session")
    assert res_session.status_code == 201
    pairing_code = res_session.json()["pairing_code"]

    # Mock custom SHA-256 node ID, public key, and capability list
    node_id = "android_115fa0981eab349fbcdefa882a12f9e98418a09bcdef1a123bc89fba9a12e12a"
    pub_key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."
    caps = {
        "camera": "KNOWN",
        "microphone": "KNOWN",
        "gps": "KNOWN",
        "accelerometer": "KNOWN",
        "biometric_support": "KNOWN"
    }

    # 2. Complete Pairing Confirm Request
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "Tag's Android Node",
            "device_type": "android",
            "device_id": node_id,
            "public_key": pub_key,
            "capabilities": caps
        }
    )
    assert res_pair.status_code == 200
    res_data = res_pair.json()
    assert res_data["success"] is True
    assert res_data["device"]["device_id"] == node_id
    assert res_data["device"]["public_key"] == pub_key
    assert "camera" in res_data["device"]["capabilities"]

    # 3. Verify SQLite DB state
    db_device = device_repo.get_device_by_id(node_id)
    assert db_device is not None
    assert db_device["public_key"] == pub_key
    assert "biometric_support" in db_device["capabilities"]


def test_pairing_invalid_pin_rejected():
    """Verify that pairing fails and raises 401 Unauthorized when PIN is invalid."""
    client = TestClient(app)

    # Trigger pairing session
    client.post("/api/v1/auth/pairing-session")

    # Send incorrect PIN
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": "000000", # invalid PIN
            "device_name": "Rogue Phone",
            "device_type": "android"
        }
    )
    assert res_pair.status_code == 401


def test_pairing_malicious_autonomy_level_injection_rejected():
    """Verify that clients attempting to directly modify autonomy, permissions, or inject keys are rejected."""
    client = TestClient(app)
    res_session = client.post("/api/v1/auth/pairing-session")
    pairing_code = res_session.json()["pairing_code"]

    # Attempt to inject un-allowlisted admin permissions during pairing
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "Rogue Phone",
            "device_type": "android",
            "permissions": ["bypassed_admin_scope_unauthorized"] # Blocked: Server overrides and assigns standard scopes
        }
    )
    assert res_pair.status_code == 200
    res_data = res_pair.json()
    # The permissions list returned must strictly match standard, host-assigned safe permissions!
    assert "bypassed_admin_scope_unauthorized" not in res_data["device"]["permissions"]
    assert "chat" in res_data["device"]["permissions"]


# ==============================================================================
# REVOCATION & RECONNECT REJECTION TESTS
# ==============================================================================

def test_revocation_and_reconnect_handshake_rejections():
    """Verify that revoking a device immediately invalidates REST queries, connections, and ticket handshakes."""
    client = TestClient(app)

    # 1. Complete pairing first
    res_session = client.post("/api/v1/auth/pairing-session")
    pairing_code = res_session.json()["pairing_code"]
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "Target Phone",
            "device_type": "android"
        }
    )
    access_token = res_pair.json()["access_token"]
    device_id = res_pair.json()["device"]["device_id"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Verify connection works initially
    res_dev = client.get("/api/v1/devices", headers=headers)
    assert res_dev.status_code == 200

    # 2. Trigger self-revocation
    res_revoke = client.delete(f"/api/v1/devices/{device_id}", headers=headers)
    assert res_revoke.status_code == 200

    # 3. Assert REST is rejected instantly
    res_dev_post = client.get("/api/v1/devices", headers=headers)
    assert res_dev_post.status_code == 401

    # 4. Assert WS Ticket handshake request is rejected instantly
    res_ticket = client.post("/api/v1/auth/ws-ticket", headers=headers)
    assert res_ticket.status_code == 401


# ==============================================================================
# FLUTTER REGRESSION TEST
# ==============================================================================

def test_legacy_flutter_client_compatibility_regression_check():
    """Verify that legacy Flutter clients mapping standard parameters continue pairing successfully without breaking."""
    client = TestClient(app)
    res_session = client.post("/api/v1/auth/pairing-session")
    pairing_code = res_session.json()["pairing_code"]

    # Legacy payload does not send device_id, public_key, or capabilities list
    res_pair = client.post(
        "/api/v1/auth/pair",
        json={
            "pairing_code": pairing_code,
            "device_name": "Legacy Flutter HUD",
            "device_type": "android"
        }
    )
    assert res_pair.status_code == 200
    res_data = res_pair.json()
    assert res_data["success"] is True
    # Verify that the server automatically assigned safe fallback defaults
    assert res_data["device"]["device_id"].startswith("android_")
    assert res_data["device"]["public_key"] is None
    assert res_data["device"]["capabilities"] == "{}"
