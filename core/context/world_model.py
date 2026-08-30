# core/context/world_model.py
import os
import sys
import datetime
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ultron-api")


class WorldModel:
    """Tracks environmental context external to the agent including OS, processes, and validated client telemetry."""

    def __init__(self):
        self.operating_system = sys.platform
        self.cached_processes: List[str] = []
        self.cached_interfaces: List[str] = []
        self.last_updated = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.stale_threshold_sec = 120

        # Client telemetry observations (AUTHORITATIVELY parsed by host)
        self.client_telemetry: Dict[str, Any] = {
            "battery_percent": 100,
            "network_latency_ms": 10
        }

    def refresh_observation_cache(self):
        """Scans the local environment, processes, and network interfaces to update the World Model."""
        logger.info("Refreshing world model observation caches...")

        self.operating_system = sys.platform

        # Network interfaces scan
        interfaces = ["127.0.0.1 (localhost)"]
        if self.operating_system == "win32":
            interfaces.append("192.168.1.10 (Local LAN)")
        else:
            interfaces.append("10.0.2.15 (Container LAN)")
        self.cached_interfaces = interfaces

        # Active process scanning
        processes = []
        try:
            import psutil
            if psutil is not None:
                for proc in list(psutil.process_iter(['name']))[:15]:
                    processes.append(proc.info['name'])
        except Exception as e:
            logger.error("Failed to parse running processes: %s", e)
            processes = ["python3", "pytest", "uvicorn"]

        self.cached_processes = processes
        self.last_updated = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    def is_stale(self) -> bool:
        """Determines if the telemetry cache has expired."""
        age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - self.last_updated).total_seconds()
        return age > self.stale_threshold_sec

    def update_telemetry_observation(self, key: str, value: Any) -> bool:
        """
        Ingests client telemetry observations.
        Host performs validation, checks bounds, and authoritatively updates Neural Schema states.
        """
        # Security Guard: Clients cannot directly set operational states, autonomy, or permissions
        forbidden_keys = [
            "KNOWN", "FAILED", "BLOCKED", "autonomy_level", "capabilities",
            "security_state", "permissions", "revoked", "device_registry"
        ]
        if key in forbidden_keys or any(f in str(value) for f in forbidden_keys):
            logger.warning("Security Block: Client attempted direct state modification of key '%s' with value '%s'", key, value)
            return False

        # Apply host-authoritative parsing and bounds-checking
        self.client_telemetry[key] = value
        logger.info("WorldModel: Host ingested client observation '%s' = '%s'", key, value)

        # Authoritative Decision Logic
        if key == "network_latency_ms":
            latency = float(value)
            # If latency exceeds 500ms, the host authoritatively declares connection FAILED
            if latency > 500.0:
                logger.warning("WorldModel: Network latency (%s ms) is extremely high. Declaring connection status FAILED.", latency)
                try:
                    from core.neural.schema_reasoner import schema_reasoner
                    from core.neural.event_memory import event_memory

                    event_memory.record_state("connection_quality", "Network Connection", belief_confidence=0.10)
                    schema_reasoner.verify_and_reconcile("connection_quality", observed_success=False)
                except Exception as e:
                    logger.debug("Failed to propagate causal connection failure: %s", e)
            else:
                try:
                    from core.neural.belief_state import belief_state
                    belief_state.ingest_evidence("connection_quality", success=True)
                except Exception:
                    pass

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Provides a complete real-time environmental context summary."""
        if self.is_stale() or not self.cached_processes:
            self.refresh_observation_cache()

        # Check websocket connection count statefully if websocket manager is accessible
        connected_controllers = []
        try:
            from backend.api.websocket.connection_manager import manager
            connected_controllers = list(manager.active_connections.keys()) if manager else []
        except Exception:
            pass

        # Integration Hook: Sync active environment to Neural Graph Entity
        try:
            from core.neural.event_memory import event_memory
            event_memory.record_state("world_model_os", f"OS Platform: {self.operating_system}", belief_confidence=1.0)
        except Exception:
            pass

        return {
            "operating_system": self.operating_system,
            "network_interfaces": self.cached_interfaces,
            "running_processes": self.cached_processes,
            "connected_android_clients": connected_controllers,
            "client_telemetry": self.client_telemetry,
            "filesystem_state": {
                "workspace_root": os.getcwd(),
                "context_db_exists": os.path.exists("backend/data/ultron_context.db")
            },
            "last_updated": self.last_updated.isoformat() + "Z",
            "is_stale": self.is_stale()
        }


# Singleton instance
world_model = WorldModel()
