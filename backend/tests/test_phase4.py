# backend/tests/test_phase4.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.server import app
from backend.database.device_repository import device_repo
from backend.api.websocket.connection_manager import manager
from backend.services.confirmation_service import confirmation_service
from backend.services.command_service import command_service

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_lockouts():
    """Ensure brute force tracking and paired states are fresh and clean."""
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")
    confirmation_service.pending_requests.clear()
    yield
    confirmation_service.pending_requests.clear()


@pytest.fixture(scope="module")
def registered_token_and_device():
    """Pair a test device and return the raw bearer token and device ID."""
    sess_resp = client.post("/api/v1/auth/pairing-session")
    pin = sess_resp.json()["pairing_code"]

    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pin,
        "device_name": "Phase 4 Test Device",
        "device_type": "android"
    })
    data = pair_resp.json()
    return data["access_token"], data["device"]["device_id"]


# ==============================================================================
# WEBSOCKET AUTHENTICATION TESTS
# ==============================================================================

def test_websocket_handshake_rejections():
    """Verify that unauthenticated WS connection attempts are strictly rejected."""
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as websocket:
            pass


def test_websocket_ticket_handshake_success(registered_token_and_device):
    """Verify that clients can exchange access tokens for short-lived tickets to connect safely without URL leaks."""
    token, device_id = registered_token_and_device
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Request short-lived single-use ticket
    ticket_resp = client.post("/api/v1/auth/ws-ticket", headers=auth_headers)
    assert ticket_resp.status_code == 201

    ticket = ticket_resp.json()["ticket"]

    # 2. Connect to WS using the ticket (Succeeds)
    with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
        handshake = websocket.receive_json()
        assert handshake["event"] == "CONNECTION_ESTABLISHED"
        assert handshake["device_id"] == device_id

    # 3. Attempt to reconnect with the same ticket (fails because single-use)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
            pass


# ==============================================================================
# CONFIRMATION WORKFLOW TESTS (DIRECT COROUTINE INTEGRATIONS)
# ==============================================================================

@pytest.mark.anyio
async def test_confirmation_approval_direct(registered_token_and_device):
    """Verify that submitting an APPROVED decision on a pending request wakes up and completes successfully."""
    _, device_id = registered_token_and_device
    cmd_id = "cmd_test_app"

    # 1. Spawn create_and_await_confirmation as a task so we can interact with it concurrently
    task = asyncio.create_task(
        confirmation_service.create_and_await_confirmation(
            command_id=cmd_id,
            device_id=device_id,
            command_name="launch_application",
            parameters={"application": "chrome"},
            timeout_seconds=5.0
        )
    )

    # Yield control to allow the session setup inside pending_requests
    await asyncio.sleep(0.01)

    # Check session created
    assert len(confirmation_service.pending_requests) == 1
    req_id = list(confirmation_service.pending_requests.keys())[0]

    # 2. Submit APPROVED response
    success = confirmation_service.submit_decision(
        request_id=req_id,
        command_id=cmd_id,
        device_id=device_id,
        decision="approved"
    )
    assert success is True

    # 3. Wait for approval and confirm results
    approved, reason = await task
    assert approved is True
    assert reason == "Approved"


@pytest.mark.anyio
async def test_confirmation_rejection_direct(registered_token_and_device):
    """Verify that submitting a REJECTED decision cancels execution."""
    _, device_id = registered_token_and_device
    cmd_id = "cmd_test_app"

    task = asyncio.create_task(
        confirmation_service.create_and_await_confirmation(
            command_id=cmd_id,
            device_id=device_id,
            command_name="launch_application",
            parameters={"application": "chrome"},
            timeout_seconds=5.0
        )
    )

    await asyncio.sleep(0.01)
    req_id = list(confirmation_service.pending_requests.keys())[0]

    # Submit REJECTED response
    success = confirmation_service.submit_decision(
        request_id=req_id,
        command_id=cmd_id,
        device_id=device_id,
        decision="rejected"
    )
    assert success is True

    approved, reason = await task
    assert approved is False
    assert reason == "Rejected"


@pytest.mark.anyio
async def test_confirmation_expiration_timeout(registered_token_and_device):
    """Verify that confirmations expire dynamically and return errors on timeout."""
    _, device_id = registered_token_and_device

    # Trigger command_service with a fast 0.1-second timeout
    res_task = asyncio.create_task(
        command_service.execute_command(
            command="launch_application",
            parameters={"application": "chrome"},
            device_id=device_id,
            timeout_seconds=0.1
        )
    )

    # Allow 0.2 seconds for timeout trigger
    await asyncio.sleep(0.2)

    # Wait for the task to finish
    result = await res_task
    assert result["success"] is False
    assert result["status"] == "rejected"
    assert "expired" in result["error"]["message"].lower()


@pytest.mark.anyio
async def test_duplicate_or_invalid_confirmation_rejections(registered_token_and_device):
    """Verify that validation checks intercept invalid or duplicate decisions securely."""
    _, device_id = registered_token_and_device
    cmd_id = "cmd_test_app"

    task = asyncio.create_task(
        confirmation_service.create_and_await_confirmation(
            command_id=cmd_id,
            device_id=device_id,
            command_name="launch_application",
            parameters={"application": "chrome"},
            timeout_seconds=5.0
        )
    )
    await asyncio.sleep(0.01)
    req_id = list(confirmation_service.pending_requests.keys())[0]

    # 1. Invalid decision payload (rejected)
    invalid_success = confirmation_service.submit_decision(
        request_id=req_id, command_id=cmd_id, device_id=device_id, decision="hack_attempt"
    )
    assert invalid_success is False

    # 2. Invalid command ID (rejected)
    invalid_cmd = confirmation_service.submit_decision(
        request_id=req_id, command_id="fake_cmd", device_id=device_id, decision="approved"
    )
    assert invalid_cmd is False

    # 3. Invalid device ID (rejected)
    invalid_dev = confirmation_service.submit_decision(
        request_id=req_id, command_id=cmd_id, device_id="fake_dev", decision="approved"
    )
    assert invalid_dev is False

    # 4. Correct response (succeeds)
    success = confirmation_service.submit_decision(
        request_id=req_id, command_id=cmd_id, device_id=device_id, decision="approved"
    )
    assert success is True
    await task
