# ULTRON-AI Authentication & Pairing Specification

This document outlines the security, authorization, and cryptographic pairing design implemented in Phase 3 of the **ULTRON-AI** connected assistant gateway.

---

## 🔒 1. Core Security Boundary Definition

Unlike basic home automation servers, ULTRON-AI does NOT treat local LAN presence or IP ownership as authorization. The host laptop enforces an absolute cryptographic boundary:

```
[ UNPAIRED CLIENT ]
         │
         ├── GET /api/v1/health ──────► [ PUBLIC ACCESS ALLOWED ]
         │
         └── Any Protected API/WS ────► [ HTTP 401 UNAUTHORIZED ]
```

---

## 🛠️ 2. Hashed SQLite Device Registry

All security records, device details, and pairing sessions are persisted securely inside a local-only, thread-safe SQLite database:
*   **Database Path:** `backend/data/ultron_devices.db` (strictly ignored by Git trackers).
*   **Auto-Deployment:** The tables are statefully verified and created on every server startup via `backend/database/connection.py:initialize_database()`.

### A. Database Table Schemas

#### 1. `devices` Registry Table
Registers all client devices successfully paired and authorized to communicate with ULTRON:
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,       -- Secure random string, e.g. "android_8fa31e..."
    device_name TEXT NOT NULL,         -- Friendly name, e.g. "Tag's Android"
    device_type TEXT NOT NULL,         -- Hardware class, e.g. "android", "web", "desktop"
    token_hash TEXT UNIQUE NOT NULL,   -- SHA-256 hash of the issued Bearer access token
    permissions TEXT NOT NULL,         -- Comma-separated allowlist, e.g. "chat,system_status,safe_commands"
    created_at TEXT NOT NULL,          -- ISO 8601 UTC timestamp
    paired_at TEXT NOT NULL,           -- ISO 8601 UTC timestamp
    updated_at TEXT NOT NULL,          -- ISO 8601 UTC timestamp
    last_seen TEXT NOT NULL,           -- UTC timestamp updated on successful communications
    revoked INTEGER DEFAULT 0          -- 1 if the device access has been revoked, otherwise 0
);
```

#### 2. `pairing_sessions` Table
Tracks active PIN matching windows to allow secure first-time client enrollments:
```sql
CREATE TABLE pairing_sessions (
    session_id TEXT PRIMARY KEY,       -- Random unique session identifier
    code_hash TEXT NOT NULL,           -- SHA-256 hash of the generated 6-digit PIN code
    created_at TEXT NOT NULL,          -- UTC timestamp
    expires_at TEXT NOT NULL,          -- UTC expiration timestamp (valid for 180 seconds)
    used INTEGER DEFAULT 0             -- 1 if used, otherwise 0
);
```

#### 3. `brute_force_tracker` Table
Enforces rate-limiting locks against network brute force attempts:
```sql
CREATE TABLE brute_force_tracker (
    ip_address TEXT PRIMARY KEY,       -- Client IP address
    failed_attempts INTEGER DEFAULT 0, -- Counter of consecutive failures
    last_attempt_at TEXT NOT NULL,     -- UTC timestamp of last failure
    locked_until TEXT                  -- Lockout timestamp (empty if active)
);
```

---

## 🔄 3. Secure Dynamic Pairing Flow

Enrollment is mediated via a high-security, dynamic PIN-matching handshake:

1.  **Generate Pairing Session (Laptop Host Loopback-Only):**
    *   *Path:* `POST /api/v1/auth/pairing-session`
    *   *Security Guard:* The gateway checks the request headers and restricts access **strictly to loopback addresses (`127.0.0.1`, `::1`, `localhost`, and `testclient`)**. Remote network devices cannot request pairing codes.
    *   *PIN Generation:* Uses Python's secure `secrets` module to generate a cryptographically random, non-incrementing **6-digit pairing PIN code** valid for exactly **180 seconds**. The server hashes it via `SHA-256` and returns the plaintext PIN.
2.  **Validation Handshake (Public REST):**
    *   *Path:* `POST /api/v1/auth/pair`
    *   The phone client submits the plaintext 6-digit pairing PIN, device name, and device type.
    *   *Rate-limiting check:* The server validates the client IP. If locked out, raises `HTTP 401`. On any mismatch, increments failed attempts. After 5 consecutive failures, the IP is locked out for 60 seconds.
3.  **Hashed Token Registry & Distribution:**
    *   On successful PIN validation, the server marks the pairing PIN used, clears any failed attempts, and creates a secure device registration.
    *   Generates a cryptographically secure random **Bearer access token** (32 bytes of secure entropy yielding a 64-character hexadecimal string).
    *   The server **hashes the token using SHA-256** and saves only the hash.
    *   **The raw, plaintext token is returned only once** in the pairing response. The server never logs or saves it in plaintext.

---

## 🔑 4. Bearer Authentication and Permission Model

Clients authorize subsequent REST or WebSocket queries using standard HTTP Authorization headers:
```http
Authorization: Bearer <access_token>
```

### A. Authentication Dependency
Each protected endpoint calls `Depends(get_current_device)` which:
1.  Extracts the raw token, hashes it using SHA-256.
2.  Performs a database lookup for the hash.
3.  Ensures the device is not flagged as `revoked`.
4.  Updates `last_seen` audit timestamps.
5.  Resolves to a trusted `AuthenticatedDevice` validation context.

### B. Device Permission Matrix
Client capabilities are strictly audited and verified against explicitly allocated scopes:

| Permission Scope | Associated Endpoints | Allowed Actions |
| :--- | :--- | :--- |
| **`chat`** | `POST /api/v1/chat` | Query the shared AI Core Brain. |
| **`system_status`** | `GET /api/v1/system/status` | Read live hardware telemetry logs. |
| **`safe_commands`** | `POST /api/v1/commands` | Trigger approved, harmless actions (`get_time`, `get_date`). |
| **`confirmation_commands`** | `POST /api/v1/commands` | Planned for Phase 4 (Mobile WebSocket authorization). |
| **`high_risk_commands`** | `POST /api/v1/commands` | Planned for Phase 4 (Double-prompt laptop confirmations). |

If a paired device tries to execute a command outside its explicitly registered permission scope, the API intercepts and rejects the request with an `HTTP 403 Forbidden` response.

---

## 🚪 5. Device Revocation & Expiry

*   **Audit-Safe Revocation:** Calling `DELETE /api/v1/devices/{device_id}` sets the `revoked` flag to `1` in SQLite instead of deleting the row. This ensures full historic transaction tracing.
*   **Immediate Access Block:** Once marked `revoked = 1`, all subsequent requests using that token hash are immediately blocked with an `HTTP 401 Unauthorized` response.
