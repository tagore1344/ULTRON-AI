# ULTRON-AI Mobile Client Setup Manual

This document provides setup, pairing, network diagnostics, and troubleshooting guidelines for connecting the **ULTRON-AI Flutter Android Client** to your Windows Laptop host.

---

## 🛠️ 1. Prerequisites and Installation

### A. Flutter Mobile Client Setup
To compile, run, or build the Android client:
1.  **Install Flutter SDK:** Ensure you possess the Flutter SDK `>= 3.0.0` installed. (Run `flutter --version` to verify).
2.  **Android Studio:** Install Android Studio and configure an Android virtual emulator (AVD) or enable USB debugging on your physical Android phone.
3.  **Navigate to Workspace:**
    ```bash
    cd mobile/ultron_mobile
    ```
4.  **Install Pub Dependencies:**
    ```bash
    flutter pub get
    ```
5.  **Compile & Run:**
    ```bash
    flutter run
    ```

### B. Laptop Host API Setup
To launch the FastAPI server gateway:
1.  **Install Backend Requirements:**
    ```bash
    python3 -m pip install -r requirements_backend.txt --break-system-packages
    ```
2.  **Launch Server on LAN Interface:**
    ```bash
    python3 -m backend.server
    ```
    *Note: Ensure the server binds to `0.0.0.0` to permit remote local Wi-Fi connections.*

---

## 🌐 2. Local LAN IP Discovery

Since `localhost` inside the Android environment addresses the phone itself, the mobile client must connect to the laptop's actual LAN IP address.

### To Find Your Laptop's Local IP Address:
*   **On Windows (PowerShell/CMD):**
    ```powershell
    ipconfig
    ```
    *Look for `IPv4 Address` under your active Wi-Fi adapter (e.g. `192.168.1.10`).*
*   **On Linux/macOS:**
    ```bash
    hostname -I
    ```

---

## 🧱 3. Windows Firewall Configuration

By default, Windows blocks incoming network traffic on unknown ports (such as `8000`). To allow the phone to reach the server, you must explicitly permit the port through Windows Defender Firewall.

### Command Line Configuration (Admin PowerShell):
Run the following command as an Administrator to open port `8000` safely:
```powershell
New-NetFirewallRule -DisplayName "ULTRON-AI API Gateway" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```
*Note: Do NOT disable Windows Firewall globally. Only allow the specific port rule above.*

---

## 🔄 4. Step-by-Step Pairing Walkthrough

When you launch the mobile application for the first time, you will be met with the pairing screen.

1.  **Generate Pairing PIN (On Host Laptop):**
    *   Trigger the localhost pairing session endpoint (e.g. via browser or cURL from the laptop itself):
        ```bash
        curl -X POST http://127.0.0.1:8000/api/v1/auth/pairing-session
        ```
    *   *Output:*
        ```json
        { "success": true, "session_id": "...", "pairing_code": "583214", "expires_at": "..." }
        ```
2.  **Input PIN on Phone:**
    *   Open the mobile application.
    *   Enter your Laptop's LAN IP URL: `http://192.168.1.10:8000`.
    *   Specify your Custom Device Name (e.g., `Tag's Phone`).
    *   Enter the active **6-digit pairing PIN code** (e.g. `583214`).
    *   Tap **PAIR AND CONNECT**.
3.  **Secure Authentication established:**
    *   The phone exchanges the temporary PIN for a secure Bearer token, writes it safely into **encrypted secure storage**, connects the stateful WebSocket channel, and displays **`● SYSTEM ONLINE`** on your HUD dashboard.

---

## 🛠️ 5. Troubleshooting & Diagnostics

*   **Error: "NETWORK_OFFLINE" on Pairing:**
    *   Verify that both the laptop and phone are connected to the exact same Wi-Fi SSID network.
    *   Verify that your laptop IP adapter is correct and you can ping it from the phone.
    *   Double-check that the Windows Defender rule is active.
*   **Error: "Access Revoked":**
    *   If the laptop administrator revokes the device's authorization ID, the WebSocket session is instantly evicted. The mobile client safely purges its token, cancels all pending requests, and returns to the Pairing screen immediately.
