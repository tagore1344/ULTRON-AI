# ULTRON-AI Security Model and Threat Audit

This document defines the comprehensive threat model, permission configurations, and cryptographic barriers implemented to guard the **ULTRON-AI laptop host** from unauthorized operations or network compromises.

> ⚠️ **CRITICAL DISCLAIMER:** ULTRON-AI is designed strictly for deployment over **private, trusted local area networks (LAN)**. Under no circumstances should the FastAPI server port (`8000`) or WebSockets be exposed directly to the public internet or mapped via unrestricted public router port-forwarding. Public WAN operations must travel through an explicitly authenticated, private virtual private network (such as **Tailscale** or **WireGuard**).

---

## 🔒 1. Multi-Tier Security Boundary Architecture

The system utilizes an automated, highly-defended, five-tier pipeline to process and execute any remote command:

```
[ PENDING REMOTE COMMAND ]
           │
           ▼
[ TIER 1: HTTP Bearer Authentication ]  ──► Validates cryptographic token hash in SQLite
           │
           ▼
[ TIER 2: Granular Scope Authorization ] ──► Audits device permissions (chat, system_status, safe_commands)
           │
           ▼
[ TIER 3: Canonical Command Allowlist ]  ──► Rejects anything outside predefined command maps
           │
           ▼
[ TIER 4: Parameter Fuzzing & Injection ]──► Blocks raw CLI sub-interpreters (python, cmd, bash, etc.)
           │
           ▼
[ TIER 5: Stateful Client Confirmation ] ──► Enforces 30-sec real-time approval window & re-validations
           │
           ▼
[ CANONICAL EXECUTION VIA TOOL REGISTRY ]
```

---

## 📐 2. Secure WAN Overlay Layer

When communicating from outside your local home Wi-Fi, connection payloads are isolated inside a secure, encrypted overlay network (Tailscale / WireGuard):

```
┌────────────────────────────────────────────────────────┐
│                   INTERNET WAN BOUNDARY                │
│                                                        │
│  [Android Phone] ──► Encrypted Tunnel ──► [Laptop Host]│
│  (Tailscale IP)      (WireGuard / AEs)    (Tailscale IP)│
│                                                │       │
│                                                ▼       │
│                                           ULTRON Core  │
└────────────────────────────────────────────────────────┘
```

---

## 🗺️ 3. Threat Model Matrix

| Threat | Target Area | Severity | Mitigation Control |
| :--- | :--- | :--- | :--- |
| **Attacker on Public Internet** | Public REST/WebSocket | **CRITICAL** | **Port-Forwarding Prohibited:** Port `8000` is bound locally and restricted by Windows Defender Firewall. No WAN routing is exposed. |
| **Compromised Overlay Node** | Private Network (Tailscale) | **HIGH** | **Zero-Trust Auth Enforced:** Private overlay membership does NOT bypass security. Paired token verification (`Authorization: Bearer <token>`) remains mandatory. |
| **Paired Phone Theft** | Device Credentials | **HIGH** | Plaintext tokens are never stored locally. Access can be instantly terminated on the host laptop using `DELETE /api/v1/devices/{device_id}`, which evicts WebSocket sessions and invalidates future hashes. |
| **Command Injection** | Local Host Terminal | **CRITICAL** | Parameters are strictly serialized into Pydantic models. Direct execution of raw CLI sub-interpreters (`python`, `powershell`, `bash`, `cmd`, etc.) is fully banned. |
| **Confirmation Replay** | System Automation | **HIGH** | Request IDs are single-use, timed to expire in 30 seconds, and validated statefully against active device session owners. |
| **Cross-Device Leakage** | Event Pushing | **MEDIUM** | Stateful `ConnectionManager` isolates socket routing (`send_to_device(device_id)`). Sockets do not receive other devices' transaction lifecycles. |

---

## 🔑 4. Token & Pairing Security

### A. Non-plaintext Storage
*   **Plaintext Banned:** Raw issued Bearer tokens or pairing PINs are never stored in plain text files, standard SharedPreferences, logs, or server-side databases.
*   **One-Time Return:** Plaintext tokens are sent over the network exactly **once** during the pairing response. Future client requests must use them inside standard headers.

### B. No long-lived Tokens in URLs
To prevent token exposures inside proxy history lists, reverse proxy logs, or diagnostics, **the long-lived Bearer token is strictly blocked from WebSocket paths**. The mobile client must connect using the **short-lived 15-second WS ticket pipeline** (REST query `POST /api/v1/auth/ws-ticket` returns a temporary ticket, which is consumed and invalidated instantly during handshake).

---

## ⚙️ 5. Device Permission Scopes

Device capabilities are strictly audited and verified against explicitly allocated scopes:

*   **`chat`:** Allowed to call `POST /api/v1/chat`.
*   **`system_status`:** Allowed to call `GET /api/v1/system/status`.
*   **`safe_commands`:** Allowed to execute harmless commands (`get_time`, `get_date`).
*   **`confirmation_commands` / `high_risk_commands`:** Disabled in current stages.

If an authenticated device attempts to invoke an endpoint outside its explicitly assigned scopes, the gateway immediately intercepts and rejects the request with an `HTTP 403 Forbidden` response.
