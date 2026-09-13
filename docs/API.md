# ULTRON-AI API Reference Manual (v1)

This document provides developers and mobile clients with the technical endpoint and protocol specification for communicating with the **ULTRON-AI Gateway Server**.

---

## 🌐 1. Server Configuration & Startup

### A. Environment Configuration (`.env`)
The backend is configured via standard system environment variables loaded via Pydantic Settings.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ULTRON_HOST` | `0.0.0.0` | IP interface to bind. Use `0.0.0.0` to listen on all local network adapters. |
| `ULTRON_PORT` | `8000` | Gateway port number. |
| `ULTRON_ENV` | `development` | Operating state (`development`, `testing`, `production`). |
| `ULTRON_LOG_LEVEL` | `INFO` | Console logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ULTRON_CORS_ORIGINS` | `*` | Configurable CORS allowed origins (JSON array or comma-separated lists). |

### B. Execution Commands
To start the FastAPI gateway server in the background or for development, use the following commands:

*   **Standard Python execution:**
    ```bash
    python3 -m backend.server
    ```
*   **Production / Direct Uvicorn execution:**
    ```bash
    uvicorn backend.server:app --host 0.0.0.0 --port 8000
    ```

---

## 🛣️ 2. REST Endpoints

### 🟢 2.1. Health Check
Checks the server health, liveness status, and current service build version.

*   **Method:** `GET`
*   **Path:** `/api/v1/health`
*   **Authorization Required:** No
*   **Request Headers:** None
*   **Response Model (`HealthResponse`):**
    ```json
    {
      "status": "healthy",
      "service": "ultron-api",
      "version": "1.0.0"
    }
    ```
*   **Status Codes:**
    *   `200 OK`: Server is active and operational.

### 🟢 2.2. Root Welcome Check
*   **Method:** `GET`
*   **Path:** `/`
*   **Authorization Required:** No
*   **Response Payload:**
    ```json
    {
      "service": "ULTRON-AI",
      "api": "v1"
    }
    ```

### 💬 2.3. AI Chat Query (`POST /api/v1/chat`)
Queries the shared ULTRON AI core brain. Includes session tracking capability.

*   **Method:** `POST`
*   **Path:** `/api/v1/chat`
*   **Authorization Required:** Planned for Phase 3 (currently development mode).
*   **Request Payload (`ChatRequest`):**
    ```json
    {
      "message": "Hello ULTRON, what is the time?",
      "conversation_id": "session_optional_123"
    }
    ```
*   **Response Payload (`ChatResponse`):**
    ```json
    {
      "success": true,
      "response": "The time is 12:00 PM, sir.",
      "conversation_id": "session_optional_123",
      "timestamp": "2026-08-11T12:00:00.000000Z"
    }
    ```
*   **Error Responses:**
    *   `422 Unprocessable Entity`: Blank, missing, or oversized message (exceeding 2000 chars) submitted.
    *   `500 Internal Server Error`: LLM execution failure or core model offline.
        ```json
        {
          "detail": {
            "success": false,
            "error": {
              "code": "ULTRON_CORE_ERROR",
              "message": "ULTRON could not process the request."
            }
          }
        }
        ```

### 📊 2.4. System Status Telemetry (`GET /api/v1/system/status`)
Exposes live hardware metrics of the host laptop (CPU, RAM, GPU, Battery, Disk Space).

*   **Method:** `GET`
*   **Path:** `/api/v1/system/status`
*   **Authorization Required:** Planned for Phase 3 (currently development mode).
*   **Response Payload (`SystemStatusResponse`):**
    ```json
    {
      "cpu": {
        "usage_percent": 12.5
      },
      "memory": {
        "usage_percent": 54.3,
        "used_mb": 8890,
        "total_mb": 16384
      },
      "disk": {
        "usage_percent": 68.12
      },
      "battery": {
        "available": true,
        "percent": 98,
        "power_plugged": true
      },
      "gpu": {
        "available": false,
        "name": "N/A",
        "usage_percent": 0
      },
      "os": {
        "name": "Linux",
        "version": "5.15.0-generic",
        "hostname": "sandbox-host"
      }
    }
    ```

### ⚙️ 2.5. Command Execution Gateway (`POST /api/v1/commands`)
Submits a secure allowlisted laptop system command to be statefully audited, validated, and executed.

*   **Method:** `POST`
*   **Path:** `/api/v1/commands`
*   **Authorization Required:** Planned for Phase 3 (currently development mode).
*   **Request Payload (`CommandRequest`):**
    ```json
    {
      "command": "launch_application",
      "parameters": {
        "application": "chrome"
      }
    }
    ```
*   **Response Payload (`CommandResponse`):**
    ```json
    {
      "success": true,
      "command_id": "cmd_b12fa481e592",
      "status": "completed",
      "result": {
        "message": "Command 'launch_application' completed successfully.",
        "response": "Opening chrome"
      }
    }
    ```
*   **Error Responses:**
    *   `400 Bad Request`: Command is not in the allowlist.
        ```json
        {
          "success": false,
          "command_id": "cmd_a32620dbda59",
          "status": "rejected",
          "error": {
            "code": "COMMAND_NOT_ALLOWED",
            "message": "Command 'format_disk_now' is not available through the API."
          }
        }
        ```
    *   `403 Forbidden`: Command is classified as `HIGH_RISK` and blocked in the Phase 2 gateway.
        ```json
        {
          "success": false,
          "command_id": "cmd_7c12fa8c13a5",
          "status": "rejected",
          "error": {
            "code": "HIGH_RISK_COMMAND_REQUIRES_AUTHORIZATION",
            "message": "This command is classified as HIGH_RISK and requires authenticated device confirmation."
          }
        }
        ```
    *   `422 Unprocessable Entity`: Raw interpreters (`python`, `powershell`, `sh`, `bash`, `cmd`, etc.) or execution scripts detected in the command name.

---

## 🔌 3. WebSocket Endpoint

Provides stateful real-time connection checking, event subscriptions, and transaction monitoring for authorized clients.

*   **URL Schemes:**
    *   `ws://<laptop-ip>:8000/ws`
    *   `ws://<laptop-ip>:8000/api/v1/ws`

### A. Connection Handshake
Upon establishing a WebSocket connection, the client instantly receives a confirmation payload:
```json
{
  "event": "CONNECTION_ESTABLISHED",
  "timestamp": "2026-08-11T12:00:00.000000Z",
  "message": "Connection to ULTRON-AI gateway established."
}
```

### B. Live Heartbeat Checking (Ping-Pong)
Clients can send standard ping checks over WebSocket to evaluate connection quality.
*   **Client Sends (JSON):**
    ```json
    {
      "event": "PING"
    }
    ```
*   **Server Responds (JSON):**
    ```json
    {
      "event": "PONG",
      "timestamp": "2026-08-11T12:00:01.123456Z"
    }
    ```

---

## 🚨 4. Standardized Error Payloads

All unexpected REST route errors automatically generate standardized error responses instead of revealing Python stack traces:
*   **Status Code:** `500 Internal Server Error`
*   **Payload Format:**
    ```json
    {
      "success": false,
      "error": {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "An internal server error occurred."
      }
    }
    ```
*The stack trace is securely logged on the host console for debugging.*
