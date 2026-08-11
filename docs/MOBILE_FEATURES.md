# ULTRON-AI Mobile HUD Features & Integration

This document defines the functional scope, network behaviors, and structural security boundaries governing the features implemented in Phase 6 of the **ULTRON-AI Mobile HUD** client app.

---

## 💬 1. Encrypted Chat Comm Channel

The Chat UI enables full real-time conversations directly with the shared laptop-bound **ULTRON AI Core Brain**:
*   **Zero Local Duplicate Brains:** The mobile client does NOT run model weights locally. It acts strictly as an interface, sending text inputs to `POST /api/v1/chat` and parsing standard outputs.
*   **Stateful Conversation ID:** On initial prompt, the backend creates a tracking `conversation_id` which the phone captures and attaches to subsequent REST requests. This ensures conversational context stays perfectly synchronized with your laptop assistant's history log.
*   **Security Disclosure Block:** Internal system prompt filters, raw API keys (Gemini/OpenAI/DeepSeek), or server stack traces are strictly filtered. The client is only provided the final clean text generated for the user.

---

## 🎙️ 2. Offline-First Speech-to-Text Voice Input

The mobile HUD includes a secure voice execution channel:
*   **Local Speech Processing:** Transcribes microphone voice prompts locally on the Android device's native speech API before sending clean string queries over REST.
*   **No Hardware Contention:** Bypasses sending raw audio files to the laptop. This fully prevents audio device lockups or recording contentions on your host PyAudio hardware.
*   **Strict Security Parity:** Under the hood, **voice commands do not bypass API security rules**. When the user says *"shutdown laptop"*, the translated text undergoes the exact same Command validation, permission checks, and `HIGH_RISK` blockages as manual text prompts.
*   **Least Privilege Permissions:** The microphone hardware permission is only requested at runtime when the user taps the mic button—never on startup.

---

## 📊 3. Live Hardware Telemetry Dashboard

Keeps track of your laptop host’s hardware statistics periodically:
*   **Polling Interval:** Automatically queries `GET /api/v1/system/status` every **5 seconds** when the screen is active, and halts polling on screen dispose to preserve network and battery life.
*   **Telemetry Gauges:** Employs minimal, clean progress bars representing active CPU/RAM/Battery metrics.
*   **Graceful fallbacks:** If certain metrics are unavailable (e.g. Battery cell is missing on a desktop host, or NVIDIA Drivers are missing on a non-GPU rig), the interface displays **`UNAVAILABLE`** instead of incorrect `0%` placeholders, matching backend telemetry specifications.

---

## ⚙️ 4. Secure Command Execution and Confirmation

Enforces strict boundaries when interacting with laptop shortcuts:
*   **Absolute Command Allowlist:** No raw terminal strings, python scripts, or terminal interpreters can be executed. Payload queries must be structured maps of allowed targets.
*   **SAFE Actions (Immediate):** `get_time`, `get_date`, `get_system_status` run immediately.
*   **CONFIRMATION_REQUIRED Actions (Approval Handshakes):** Launching application (Chrome), taking screenshots, and volume triggers pause execution.
*   **Real-time Approval Popups:** The server fires a WebSocket `CONFIRMATION_REQUEST` packet with a **30-second countdown**. The mobile client displays an overlay window where the user can click `CANCEL` or `CONFIRM`:
```
   ULTRON REQUEST
   Launch Chrome?
   This action opens Chrome on your laptop.
   Expires in 27 seconds.
   [ CANCEL ]   [ CONFIRM ]
```
*   **Authorization Submission:** On click, the phone returns a validated `CONFIRMATION_RESPONSE` payload back over the stateful, authenticated WebSocket channel. Once validated, the server executes the tool and broadcasts standard progress states (`COMMAND_STARTED` ──► `COMMAND_COMPLETED`), which the phone tracks inside a persistent **HUD Activity Log**.
*   **HIGH_RISK Actions Blocked:** Computer reboots, disk formats, and shutdowns remain blocked, returning strict `HTTP 403 Forbidden` payloads in Phase 6 gateway setups.
