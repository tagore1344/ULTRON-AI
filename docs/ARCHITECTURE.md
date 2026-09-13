# ULTRON-AI Distributed Ecosystem Architecture

This document defines the production-grade architectural specification for transforming **ULTRON-AI** into a secure, robust, and extensible multi-device ecosystem. The architecture anchors a single Windows Laptop host as the canonical execution, automation, and AI orchestrator, communicating securely with remote clients (e.g. Flutter Android mobile apps) over local and private networks.

---

## 📐 1. Visual Structural Architecture

```
                               ┌─────────────────┐
                               │     ULTRON      │
                               └────────┬────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                    ┌─────────┐                   ┌─────────┐
                    │  CORE   │                   │ DEVICE  │
                    │ ENGINE  │                   │ SYSTEM  │
                    └────┬────┘                   └────┬────┘
                         │                             │
          ┌──────────────┼──────────────┐        ┌─────┴─────┐
          ▼              ▼              ▼        ▼           ▼
       AI LAYER     MEMORY LAYER   AGENT LAYER Laptop      Phone
          │              │              │                    │
          └──────────────┼──────────────┘              ┌─────▼─────┐
                         │                             │   Future  │
                  ┌──────▼──────┐                      │  Devices  │
                  │ TOOL LAYER  │                      └─────┬─────┘
                  │  (Single    │                            │
                  │  Registry)  │                            │
                  └──────┬──────┘                            │
                         │                                   │
                         └──────────────┬────────────────────┘
                                        │
                               ┌────────▼────────┐
                               │ API + WebSocket │
                               │  (FastAPI v1)   │
                               └────────┬────────┘
                                        │
                               ┌────────▼────────┐
                               │ AUTH + SECURITY │
                               │ (Bearer Tokens) │
                               └────────┬────────┘
                                        │
                               ┌────────▼────────┐
                               │ DEVICE PAIRING  │
                               │  (SQLite DB)    │
                               └─────────────────┘
```

---

## 🧱 2. System Architecture Layers

The ULTRON-AI ecosystem is divided into the following isolated, highly maintainable logical layers:

### 🧠 2.1. AI, Agent, and Memory Layer
*   **AI Orchestration:** Exposes conversational capabilities by wrapping `AIOrchestrator` (`ai/orchestrator/ai_orchestrator.py`). Dispatches queries across Gemini, OpenAI, and DeepSeek, performing consensus merging.
*   **Memory Core:** Interacts with persistent file-backed logs (`conversation_memory.py`), ephemeral runtime states (`session_memory.py`), and sparse vector stores (`vector_memory.py`).

### 🛠️ 2.2. Tool & Automation Layer (Single Canonical Source of Truth)
*   **Unified Registry:** To prevent code drift and fragmentation, **`core/tools/tool_registry.py` is established as the single canonical Tool Registry**.
*   **Backward Compatibility Wrappers:** To avoid breaking your legacy voice loop GUI (`assistant_with_brain.py`), we implement a thin compatibility wrapper around the old root-level `tool_registry.py` that delegates its executions back to the canonical `core/tools/tool_registry.py`.
*   **Benefit:** Adding a new tool/capability in the future requires editing only **one** registry, automatically making it available to both Laptop Voice and Mobile API.

### 📱 2.3. Device & Session Layer (The Device System)
This new subsystem operates inside `devices/` directory and manages all client connections:
*   `device_registry.py`: Communicates with a lightweight SQLite database (`backend/data/ultron_devices.db`) to persist paired devices, names, hashes of tokens, and custom permissions.
*   `device_manager.py`: Handles CRUD operations for paired clients, device status monitoring, and active connections.
*   `pairing_manager.py`: Manages the 6-digit numeric pairing state machine (expiry check, code generation, client token distribution).
*   `session_manager.py`: Manages ephemeral WebSocket connections and links active socket IDs to authenticated devices.

### 🌐 2.4. API & Network Gateway Layer
*   **FastAPI Engine:** Binds to host port `8000` (LAN-accessible). Outfitted with Pydantic payload schemas and robust exception filters.
*   **Route Namespaces (`/api/v1`):**
    *   `GET /api/v1/health`: Uptime, engine states, and system network liveness.
    *   `POST /api/v1/auth/pair`: Endpoint to exchange temporary 6-digit pairing PINs for authenticated Bearer tokens.
    *   `POST /api/v1/chat`: Exposes standard chat query pipelines with the AI Core.
    *   `POST /api/v1/command`: Receives command payloads, routing them through the stateful Command execution lifecycle.
    *   `GET /api/v1/system/status`: Exposes hardware statistics (CPU, Memory, Battery, Storage, GPU).

### 🔌 2.5. WebSocket Event Layer
*   **Connection Manager:** Performs active heartbeat checking and pushes raw event packets to active client channels.
*   **Broadcast Pipelines:** Streams structural hardware telemetries, command logs, dynamic confirmation prompts, and user alerts.

---

## 🔒 3. Robust Security & Authentication

### 3.1. Hashed Bearer Tokens
The mobile client and any other remote clients must authorize requests using standard HTTP headers:
```http
Authorization: Bearer <access_token>
```
*   **Token Protection:** To prevent leaks of critical API keys or raw tokens, **the server never stores raw authentication tokens in plaintext**.
*   **Verification:** The SQLite device registry stores a secure hash of the token (`SHA-256` or equivalent). When a client sends a token, the API hashes it and compares it with the database.
*   **Token Revocation:** Tokens can be instantly revoked by updating the `revoked` flag in the SQLite registry:
```
devices Table:
├── device_id (text, PK)
├── device_name (text)
├── device_type (text)
├── token_hash (text)
├── created_at (timestamp)
├── last_seen (timestamp)
├── revoked (boolean)
└── permissions (text)
```

---

## 🔄 4. Command Execution Lifecycle

All command requests follow an explicit, highly traceable lifecycle:

```
  Mobile Client                    FastAPI Gateway                Tool Registry / OS
  ┌───────────┐                     ┌───────────┐                    ┌───────────┐
  │  Request  ├────────────────────►│  Receive  │                    │           │
  │  Command  │                     │  Command  │                    │           │
  └───────────┘                     └─────┬─────┘                    └───────────┘
                                          │
                                   Validate Session
                                   & Token Hashing
                                          │
                                   Permission Class
                                   Security Filter
                                          │
                                ┌─────────┴─────────┐
                                │                   │
                                ▼                   ▼
                             [ SAFE ]      [ CONFIRMATION / ]
                            (Stats, Time)  [  HIGH RISK    ]
                                │                   │
                                │         Broadcast WS Prompt
                                │         with 30-sec Timeout
                                │                   │
                                │       ┌───────────┴───────────┐
                                │       ▼                       ▼
                                │    Approved               Timeout /
                                │   by Mobile                Rejected
                                │       │                       │
                                ▼       ▼                       ▼
                            ┌───────────────┐               ┌───────────────┐
                            │  Run Command  │               │ Cancel Run &  │
                            │  via Registry │               │ Log Rejection │
                            └───────┬───────┘               └───────┬───────┘
                                    │                               │
                                    ▼                               ▼
                            [COMPLETED Event]               [REJECTED Event]
```

### 4.1. Lifecycle Events Logging
For telemetry and debugging, each step fires an event log packet over WebSocket/logs:
1.  `COMMAND_RECEIVED`: Command payload parses successfully; assigned a unique tracking `command_id` (e.g. `cmd_8f32a1`).
2.  `COMMAND_AUTHORIZED` / `COMMAND_REJECTED`: Authentication, permission levels, and validation checks resolve.
3.  `COMMAND_STARTED`: Subprocess/system executor initiates task.
4.  `COMMAND_COMPLETED`: Task successfully executes; returns execution payloads.

### 4.2. Command Classification and Permission Levels
Commands are strictly allowlisted and mapped to these three security classes:

| Class | Examples | Action Flow |
| :--- | :--- | :--- |
| **SAFE** | Telemetry status, weather, current time, battery levels, RAM/CPU diagnostics | **Immediate Execution:** Run instantly without prompting. |
| **CONFIRMATION_REQUIRED** | Launch application, terminate application, open website, volume changes | **Mobile UI Approval:** Pauses execution, broadcasts a `CONFIRMATION_REQUEST` packet to client HUD, awaits response. |
| **HIGH_RISK** | Computer shutdown, computer restart, lock screen | **Double Approval Prompt:** Prompts Mobile client UI. In addition, an **optional desktop confirmation window** (ALLOW/DENY) is rendered on the laptop screen to block malicious remote triggers if the phone is compromised. |

### 4.3. WebSocket Confirmation Timeout & Payload Validation
To prevent the server from hanging indefinitely if a client disconnects while a confirmation is outstanding:
*   **Timeout Guard:** The gateway applies a strict **30-second timeout** on confirmation requests. If no validated authorization payload is received within 30 seconds, the command transitions to `COMMAND_REJECTED` and cancels.
*   **Payload Validation:** To prevent injection attacks, confirmation messages returned over WebSocket must match this exact validation envelope:
```json
{
  "event": "CONFIRMATION_RESPONSE",
  "request_id": "req_abc123",
  "command_id": "cmd_8f32a1",
  "device_id": "android_01",
  "decision": "approved",
  "timestamp": "2026-08-11T12:00:00Z"
}
```
*The server strictly matches `request_id`, verifies the active authenticated `device_id`, and checks the expiration timestamp before allowing execution.*

---

## 🎨 5. Premium Futuristic Mobile UI Guidelines

The Flutter client interface rejects over-cluttered retro neon styling in favor of a **Clean, Premium Futuristic aesthetic** that prioritizes usability, clarity, and precision:

*   **Color Palette:** Deep Obsidian backgrounds (`#0a0f19`), space dark surfaces (`#141d2e`), crisp cyan indicators (`#00d4ff`), and warning amber (`#ffb000`) for confirmation workflows.
*   **Interface HUD Layout:**
    *   **Header:** Persistent system online indicator (`● ONLINE`) and host laptop name/battery health metrics.
    *   **Body Content:** High-fidelity, smooth SVG status gauges (CPU, RAM, GPU) and a minimal, smooth voice assistant prompt area.
    *   **Footer:** Contextual quick action buttons (Launch Browser, Take Screenshot, Lock Screen, Get Active Windows).
*   **Typography:** Strict sans-serif font structure (e.g., `Roboto Mono` or `Consolas` for system stats, `Inter` or `SF Pro` for general reading) maintaining clean dark grids.
