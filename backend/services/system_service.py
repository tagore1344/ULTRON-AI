# backend/services/system_service.py
import logging
import platform
import subprocess
import shutil
import psutil

logger = logging.getLogger("ultron-api")


class SystemService:
    """Collects secure host hardware telemetry metrics (CPU, RAM, GPU, Battery, OS)."""

    def get_cpu_info(self) -> dict:
        return {
            "usage_percent": float(psutil.cpu_percent(interval=0.1))
        }

    def get_memory_info(self) -> dict:
        mem = psutil.virtual_memory()
        return {
            "usage_percent": float(mem.percent),
            "used_mb": int(mem.used / (1024 * 1024)),
            "total_mb": int(mem.total / (1024 * 1024))
        }

    def get_disk_info(self) -> dict:
        # Check root disk usage
        total, used, free = shutil.disk_usage("/")
        usage_percent = (used / total) * 100
        return {
            "usage_percent": float(round(usage_percent, 2))
        }

    def get_battery_info(self) -> dict:
        battery = psutil.sensors_battery()
        if battery is not None:
            return {
                "available": True,
                "percent": int(battery.percent),
                "power_plugged": bool(battery.power_plugged)
            }
        return {
            "available": False,
            "percent": 0,
            "power_plugged": False
        }

    def get_gpu_info(self) -> dict:
        """Retrieves NVIDIA GPU metrics safely via nvidia-smi with timeouts and exception filters."""
        # Check if nvidia-smi is installed on host path
        nvidia_smi_path = shutil.which("nvidia-smi")
        if not nvidia_smi_path:
            return {
                "available": False,
                "name": "N/A",
                "usage_percent": 0
            }

        try:
            # Query nvidia-smi safely for name and utilization
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3,
                shell=False
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                gpu_name = parts[0].strip()
                gpu_util = int(parts[1].strip()) if len(parts) > 1 else 0
                return {
                    "available": True,
                    "name": gpu_name,
                    "usage_percent": gpu_util
                }
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi query timed out.")
        except Exception as e:
            logger.debug("GPU query fallback: %s", e)

        return {
            "available": False,
            "name": "N/A",
            "usage_percent": 0
        }

    def get_os_info(self) -> dict:
        return {
            "name": platform.system(),
            "version": platform.release(),
            "hostname": platform.node()
        }

    def get_telemetry(self) -> dict:
        """Assembles unified metrics packet securely."""
        return {
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "battery": self.get_battery_info(),
            "gpu": self.get_gpu_info(),
            "os": self.get_os_info()
        }


# Singleton instance of system metrics manager
system_service = SystemService()
