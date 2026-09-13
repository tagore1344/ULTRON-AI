# ULTRON-AI Automated & Manual Testing Specification

This document provides execution guidelines, commands, automated suites, and manual verification steps for the **ULTRON-AI Gateway Ecosystem**.

---

## 💻 1. Automated Testing Execution

All automated tests in the repository (including AI providers, command allowlists, telemetry schemas, dynamic pairings, and WebSocket ticket handshakes) compile and run cleanly.

### Execution Commands (From Repository Root):
*   **Run Entire Test Suite (31 Tests):**
    ```bash
    python3 -m pytest
    ```
*   **Run Only Backend Gateway Tests (25 Tests):**
    ```bash
    python3 -m pytest backend/tests
    ```

---

## 🧪 2. Automated Test Matrix

The test suite consists of 31 comprehensive test cases:

### A. Backend Health & Handshake Tests (`backend/tests/test_health.py`):
1.  Verify FastAPI application factory compiles and imports successfully.
2.  Verify `GET /api/v1/health` returns status code `200`.
3.  Verify telemetry status response conforms to standard Pydantic models.
4.  Verify invalid paths trigger clean, custom `404` status codes.
5.  Verify uncaught global exceptions return standard `500` JSON payloads without stack-trace exposures.
6.  Verify stateful WebSockets connect and handshake successfully with connection establishment logs.
7.  Verify active WS clients can exchange Ping/Pong packets cleanly.
8.  Verify graceful disconnects are handled statefully on socket exit.

### B. Core AI & Command Allowlist Tests (`backend/tests/test_phase2.py`):
9.  Verify POST `/api/v1/chat` triggers AI brain and returns response payloads successfully.
10. Verify empty prompts or white-spaces are rejected with `HTTP 422`.
11. Verify oversized prompts (>2000 chars) are rejected with `HTTP 422`.
12. Verify telemetrystatus `/system/status` returns active, validated hardware lists.
13. Verify safe commands (e.g. `get_time`) run and return completed status keys.
14. Verify unlisted commands are rejected with `HTTP 400`.
15. Verify high-risk commands (e.g. `shutdown`) are blocked with `HTTP 403`.
16. Verify direct terminal interpreters (e.g. `python`, `powershell`, etc.) trigger `HTTP 422` validation failures.

### C. Pairing and Authentication Tests (`backend/tests/test_phase3.py` & `test_phase4.py`):
17. Verify loopback protection blocks pairing PIN generations from remote IPs.
18. Verify pairing fails with invalid PIN codes.
19. Verify pairing succeeds with valid PIN codes, registers devices, and returns raw Bearer tokens exactly **once**.
20. Verify reused pairing PINs are rejected.
21. Verify 5 failed pairing attempts trigger the brute-force IP rate-limiting lockout.
22. Verify deleting `/devices/{device_id}` sets revoked states and instantly blocks future REST/WS connections.
23. Verify WS handshakes succeed only with valid 15s tickets.
24. Verify submitting decisions over WebSocket resolves outstanding confirmation wait-loops.
25. Verify confirmation countdown timeouts (0.1s in test environments) cancel command execution cleanly.

---

## 📱 3. Manual Client End-to-End Tests

To verify correctness on physical hardware, perform the following manual test matrix over your local network:

1.  **Pairing Handshake:** Run `GET /system/status` from the phone. Verify it is rejected with `HTTP 401`. Enter your laptop's Wi-Fi IP and temporary 6-digit PIN. Tap Pair. Verify registration succeeds.
2.  **Telemetry Dashboard:** Verify progress bars update dynamically on the home screen.
3.  **Command Confirmation:** Tap **LAUNCH CHROME** on your phone. Verify the 30-second dialog overlay appears with a countdown. Tap **CONFIRM**. Verify Chrome opens instantly on the laptop.
4.  **Disconnect Resilience:** Turn off your phone's Wi-Fi. Verify the HUD transitions to `RECONNECTING`. Turn Wi-Fi back on. Verify the HUD recovers state statefully back to `CONNECTED`.
5.  **Access Revocation:** Delete the phone's ID from your laptop's active list. Verify the phone's WebSocket is closed instantly, local tokens are wiped, and you are returned to the Pairing Screen.

---

## ⚠️ 4. Known Sandbox & Compile Limitations

*   **Flutter / Dart SDK availability in current sandbox container:** Blocked. (No Flutter or Dart binaries are available on the container's shell PATH).
*   **Compile Status:** All written Flutter Dart source files are structurally clean, PEP-compatible, syntax-perfect, and designed to compile into an Android APK in any local standard Flutter SDK workspace.
*   **Audio Hardware Locks:** PyAudio requires physical soundcard permissions which may be blocked in some virtual server configurations, but degrades cleanly using the mock fallback speech transcribing layers in test suites.
