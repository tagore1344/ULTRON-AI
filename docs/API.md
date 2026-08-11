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

---

## 🔌 3. WebSocket Endpoint

Provides stateful real-time connection checking, event subscriptions, and transaction monitoring for authorized clients.

*   **URL Schemes:**
    *   `ws://<laptop-ip>:8000/ws`
    *   `ws://<laptop-ip>:8000/api/v1/ws`
*   **Authorization Required:** Planned for Phase 3.

### A. Connection Handshake
Upon establishing a WebSocket connection, the client instantly receives a confirmation payload:
```json
{
  "event": "CONNECTION_ESTABLISHED",
  "timestamp": "2026-08-11T12:00:00.000000Z",
  "message": "Connection to ULTRON-AI system authorized successfully."
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
