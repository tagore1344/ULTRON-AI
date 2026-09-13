# backend/tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from backend.server import app


# Initialize the robust FastAPI test client with raise_server_exceptions=False
# This ensures that FastAPI exception handlers process unhandled exceptions during testing.
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def ws_authenticated_ticket():
    """Helper fixture to pair a device and retrieve a valid WebSocket handshake ticket."""
    session_response = client.post("/api/v1/auth/pairing-session")
    pairing_pin = session_response.json()["pairing_code"]

    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Health WS Test Device",
        "device_type": "android"
    })
    token = pair_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    ticket_resp = client.post("/api/v1/auth/ws-ticket", headers=auth_headers)
    return ticket_resp.json()["ticket"]


def test_1_server_imports_successfully():
    """Verify that the FastAPI application module compiles and imports successfully."""
    assert app is not None


def test_2_health_endpoint_returns_200():
    """Verify that GET /api/v1/health returns HTTP 200 OK status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_3_health_response_contents():
    """Verify that GET /api/v1/health returns standard Pydantic HealthResponse schemas."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert data["status"] == "healthy"
    assert data["service"] == "ultron-api"


def test_4_invalid_route_returns_404():
    """Verify that querying a non-existent endpoint results in a clean 404 response."""
    response = client.get("/api/v1/non_existent_route")
    assert response.status_code == 404


def test_5_unhandled_error_returns_clean_500():
    """Verify that unexpected global exceptions return standard error payloads instead of stack traces."""
    # Temporarily register a route that triggers an unhandled ZeroDivisionError
    @app.get("/api/v1/test_error")
    async def trigger_error():
        return 1 / 0

    response = client.get("/api/v1/test_error")
    assert response.status_code == 500

    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "message" in data["error"]


def test_6_websocket_handshake(ws_authenticated_ticket):
    """Verify that an authorized client can connect to the WS endpoint and receive CONNECTION_ESTABLISHED."""
    with client.websocket_connect(f"/ws?ticket={ws_authenticated_ticket}") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "CONNECTION_ESTABLISHED"
        assert "timestamp" in data
        assert "message" in data


def test_7_websocket_ping_pong_echo(ws_authenticated_ticket):
    """Verify that active WebSocket clients can ping-pong exchange messages cleanly."""
    # We must generate a fresh single-use ticket since tickets are single-use
    session_response = client.post("/api/v1/auth/pairing-session")
    pairing_pin = session_response.json()["pairing_code"]
    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Health WS Test Device 2",
        "device_type": "android"
    })
    token = pair_resp.json()["access_token"]
    ticket_resp = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    fresh_ticket = ticket_resp.json()["ticket"]

    with client.websocket_connect(f"/api/v1/ws?ticket={fresh_ticket}") as websocket:
        # Clear handshake packet
        _ = websocket.receive_json()

        # Send a secure PING event
        websocket.send_json({"event": "PING"})

        # Receive PONG reply
        response = websocket.receive_json()
        assert response["event"] == "PONG"
        assert "timestamp" in response


def test_8_websocket_disconnect_is_graceful(ws_authenticated_ticket):
    """Verify that client disconnection is handled statefully and does not cause server disruption."""
    session_response = client.post("/api/v1/auth/pairing-session")
    pairing_pin = session_response.json()["pairing_code"]
    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pairing_pin,
        "device_name": "Health WS Test Device 3",
        "device_type": "android"
    })
    token = pair_resp.json()["access_token"]
    ticket_resp = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    fresh_ticket = ticket_resp.json()["ticket"]

    with client.websocket_connect(f"/ws?ticket={fresh_ticket}") as websocket:
        # Receive handshake
        data = websocket.receive_json()
        assert data["event"] == "CONNECTION_ESTABLISHED"
    # Exiting the block performs a clean, stateful disconnection.
