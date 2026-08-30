# ULTRON-AI WebSocket Protocol Guide

This document defines the real-time event, telemetry, and transactional confirmation protocols managed over WebSockets in the **ULTRON-AI** connected gateway.

---

## 🔒 1. Handshake & Security Authentication

To prevent credentials leaking in reverse proxy logs, diagnostics, or browser histories, **ULTRON-AI strictly blocks long-lived Bearer tokens in raw query strings (`?token=...`)**.

Instead, clients must use one of these two secure handshake methods:

### A. HTTP Handshake Header (Preferred)
Provide standard HTTP Authorization headers during initial WebSocket handshakes:
```http
Authorization: Bearer <access_token>
```

### B. Short-Lived Single-Use WS Ticket (Fallback)
If the client cannot easily configure handshake headers, use a short-lived handshake credential ticket:
1.  **Request Ticket:** Perform an authenticated REST call `POST /api/v1/auth/ws-ticket` using Bearer auth.
2.  **Receive Ticket:** Returns a cryptographically secure random ticket (valid for 15 seconds and single-use).
3.  **Establish WebSocket:** Connect within 15 seconds:
    ```http
    ws://<laptop-ip>:8000/ws?ticket=<single_use_ticket>
    ```
    *The server validates, maps to the device, and instantly destroys the ticket, leaving zero compromise risk if logs are read.*

If neither credential is valid or the associated device has been revoked, the server immediately rejects the handshake with standard code `1008 Policy Violation` and closes the socket.

---

## 📦 2. Standard Event Envelope

Every event exchanged over the WebSocket channel utilizes a structured JSON envelope:
```json
{
  "event": "EVENT_NAME_STRING",
  "event_id": "evt_unique_12_hex",
  "timestamp": "ISO_8601_UTC_TIMESTAMP",
  "device_id": "android_optional_id",
  "command_id": "cmd_optional_id",
  "request_id": "req_optional_id",
  "data": {}  -- Custom event data payload dictionary
}
```

---

## 📣 3. Supported Event Types

| Event Name | Direction | Trigger Phase | Description |
| :--- | :--- | :--- | :--- |
| `CONNECTION_ESTABLISHED` | Server -> Client | Handshake Success | Signals successful connection and shares session tracking meta. |
| `PING` | Client -> Server | Heartbeat Check | Keep-alive check to verify connection liveness. |
| `PONG` | Server -> Client | Heartbeat Response| Returns a heartbeat echo back to client. |
| `CONFIRMATION_REQUEST` | Server -> Client | Command Validation| Pauses a `CONFIRMATION_REQUIRED` command and awaits mobile authorization. |
| `CONFIRMATION_RESPONSE` | Client -> Server | User Interaction | Client submits approved/rejected decisions. |
| `CONFIRMATION_EXPIRED` | Server -> Client | Timeout Trigger | Signals that the 30-second approval window expired. |
| `COMMAND_RECEIVED` | Server -> Client | Lifecycle Audit | Command payload received. |
| `COMMAND_VALIDATED` | Server -> Client | Lifecycle Audit | Payload parses successfully against schemas. |
| `COMMAND_CLASSIFIED` | Server -> Client | Lifecycle Audit | Permission level verified (`SAFE`, `CONFIRMATION_REQUIRED`). |
| `COMMAND_AUTHORIZED` | Server -> Client | Lifecycle Audit | Command is authorized to run. |
| `COMMAND_STARTED` | Server -> Client | Lifecycle Audit | Subprocess tools started execution. |
| `COMMAND_COMPLETED` | Server -> Client | Lifecycle Audit | Subprocess completed successfully. |
| `COMMAND_FAILED` | Server -> Client | Lifecycle Audit | Tool execution failed. |
| `COMMAND_REJECTED` | Server -> Client | Lifecycle Audit | Command rejected due to invalid context/permission scopes. |

---

## 🔄 4. Command Confirmation Protocol

When a paired device submits a `CONFIRMATION_REQUIRED` action (e.g. `launch_application`), the server pauses, assigns a unique tracking `command_id` / `request_id`, and pushes a confirmation request to the associated device:

### A. Server Pushes `CONFIRMATION_REQUEST`
```json
{
  "event": "CONFIRMATION_REQUEST",
  "event_id": "evt_bf812cda4521",
  "request_id": "req_a12f9b8cde42",
  "command_id": "cmd_5c128fda901b",
  "device_id": "android_efb0b75f104e",
  "timestamp": "2026-08-11T12:00:00.000000Z",
  "data": {
    "command": "launch_application",
    "description": "Launch Chrome",
    "expires_in": 30
  }
}
```

### B. Mobile Responds with `CONFIRMATION_RESPONSE`
To approve or reject, the client must return a validated JSON payload matching the envelope within **30 seconds**:
```json
{
  "event": "CONFIRMATION_RESPONSE",
  "request_id": "req_a12f9b8cde42",
  "command_id": "cmd_5c128fda901b",
  "device_id": "android_efb0b75f104e",
  "decision": "approved",  -- Must be exactly "approved" or "rejected"
  "timestamp": "2026-08-11T12:00:15.000000Z"
}
```

### C. Validation & Timeout Guards
*   **Time-Limit Block:** If no validated approved response is received within **30 seconds**, the transaction times out. The server broadcasts `CONFIRMATION_EXPIRED` to the client, cancels execution, and deletes tracking references.
*   **Disconnect Guard:** If the device disconnects or network connection drops during a pending approval, the request immediately transitions to `CANCELLED` state and aborts.
*   **Deep Payload Validation:** The server strictly validates `request_id`, verifies the active authenticated `device_id`, matches the active `command_id`, and checks that the device hasn't been revoked. Any mismatch is instantly rejected and blocked.
