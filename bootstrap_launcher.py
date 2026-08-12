# bootstrap_launcher.py
import os
import sys
import json
import time
import subprocess
import requests

ACTIVE_RELEASE_FILE = "active_release.json"


def load_active_release_path() -> str:
    """Read the active release JSON pointer, returning the path or empty if initial."""
    if os.path.exists(ACTIVE_RELEASE_FILE):
        try:
            with open(ACTIVE_RELEASE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("application_version", "1.0.0")
            if version == "1.0.0":
                return "." # Initial root releases context
            return os.path.join("releases", f"release_v{version.replace('.', '_')}")
        except:
            pass
    return "."


def main():
    print("[BOOTSTRAP] Launching ULTRON-AI process coordinator...")

    release_path = load_active_release_path()
    print(f"[BOOTSTRAP] Active release path resolved: '{release_path}'")

    # Resolve python executable path
    python_exe = sys.executable or "python3"

    # Spawn the FastAPI server gateway asynchronously
    print("[BOOTSTRAP] Spawning uvicorn server gateway process...")
    try:
        proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=release_path,
            shell=False
        )

        # 1. Statefully monitor and health check on startup
        time.sleep(3.0)

        # Attempt standard health check REST query
        try:
            resp = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=2)
            if resp.status_code == 200:
                print("[BOOTSTRAP] ✅ Health check passed. ULTRON is active and serving clients.")
                proc.wait()
                return
        except Exception as e:
            print(f"[BOOTSTRAP ERROR] Health check failed: {e}")

        # 2. Revert active release on startup crash (Zero-Residual Fallback)
        print("[BOOTSTRAP ERROR] Process crashed or reported non-healthy state on boot. Initiating rollback...")
        proc.terminate()

        # Revert pointer atomically back to initial root context
        if os.path.exists(ACTIVE_RELEASE_FILE):
            try:
                with open(ACTIVE_RELEASE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"application_version": "1.0.0"}, f, indent=4)
                print("[BOOTSTRAP] Active release pointer successfully reverted to 1.0.0.")
            except:
                pass

    except Exception as e:
        print(f"[BOOTSTRAP CRITICAL] Coordination failure: {e}")


if __name__ == "__main__":
    main()
