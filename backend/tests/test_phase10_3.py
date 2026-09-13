# backend/tests/test_phase10_3.py
import pytest
import sqlite3
import datetime
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from backend.server import app
from backend.database.device_repository import device_repo
from backend.database.connection import get_db_connection
from backend.security.token_service import token_service
from core.context.world_model import world_model
from core.context.self_model import self_model
from core.neural.neural_memory import neural_memory
from core.neural.neural_schema import NeuralNodeModel, NeuralEdgeModel
from core.agent.planner import planner


@pytest.fixture(autouse=True)
def clean_telemetry_and_context_states():
    """Wipes contextual databases and resets state coordinates before and after each test."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices")
    cursor.execute("DELETE FROM brute_force_tracker")
    conn.commit()
    conn.close()

    conn_neural = neural_memory.get_connection()
    cursor_neural = conn_neural.cursor()
    cursor_neural.execute("DELETE FROM neural_edges")
    cursor_neural.execute("DELETE FROM neural_nodes")
    conn_neural.commit()
    conn_neural.close()

    # Reset world model telemetry cache
    world_model.client_telemetry = {
        "battery_percent": 100,
        "network_latency_ms": 10
    }
    world_model.last_updated = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    yield

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices")
    cursor.execute("DELETE FROM brute_force_tracker")
    conn.commit()
    conn.close()

    conn_neural = neural_memory.get_connection()
    cursor_neural = conn_neural.cursor()
    cursor_neural.execute("DELETE FROM neural_edges")
    cursor_neural.execute("DELETE FROM neural_nodes")
    conn_neural.commit()
    conn_neural.close()


def test_telemetry_validation_accepts_safe_keys():
    """Verify that the host-authoritative WorldModel accepts and records safe, raw client telemetry observations."""
    # 1. Update battery_percent to 18 (safe key)
    success = world_model.update_telemetry_observation("battery_percent", 18)
    assert success is True
    assert world_model.client_telemetry["battery_percent"] == 18


def test_malicious_telemetry_state_injection_rejected():
    """Verify that clients are strictly forbidden from directly injecting operational states, capabilities, or permissions."""
    # Direct attempt to declare a component FAILED is rejected to enforce Host Authority
    success_state = world_model.update_telemetry_observation("microphone", "FAILED")
    assert success_state is False

    # Attempt to directly hijack autonomy level parameters is blocked
    success_autonomy = world_model.update_telemetry_observation("autonomy_level", 5)
    assert success_autonomy is False


def test_rest_api_telemetry_ingestion_and_host_authority_rejection():
    """Verify the endpoint POST /context/sync/telemetry accepts safe telemetry but raises 403 Forbidden on malicious injections."""
    client = TestClient(app)

    # 1. Register paired/authenticated device with permissions
    token = "access_token_telemetry_sync"
    token_hash = token_service.hash_string(token)
    device_repo.create_device({
        "device_id": "phone_sync_01",
        "device_name": "Sync Phone",
        "device_type": "android",
        "token_hash": token_hash,
        "permissions": ["system_status"],
        "created_at": "2026-08-13T12:00:00Z",
        "paired_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T12:00:00Z",
        "last_seen": "2026-08-13T12:00:00Z",
        "revoked": False
    })

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Post safe telemetry (should succeed)
    payload_safe = {
        "items": [
            {"key": "battery_percent", "value": 45},
            {"key": "network_latency_ms", "value": 83}
        ]
    }
    res_safe = client.post("/api/v1/context/sync/telemetry", json=payload_safe, headers=headers)
    assert res_safe.status_code == 200
    assert world_model.client_telemetry["battery_percent"] == 45
    assert world_model.client_telemetry["network_latency_ms"] == 83

    # 3. Post forbidden state injection (should trigger 403 Forbidden)
    payload_forbidden = {
        "items": [
            {"key": "autonomy_level", "value": 5}
        ]
    }
    res_forbidden = client.post("/api/v1/context/sync/telemetry", json=payload_forbidden, headers=headers)
    assert res_forbidden.status_code == 403
    assert "prohibited" in res_forbidden.json()["detail"]


def test_high_latency_observation_triggers_authoritative_neural_failure_cascade():
    """Verify that when client reports high latency (>500ms), the host authoritatively declares connection FAILED and propagates it."""
    # Seed connection quality conceptually
    from core.neural.concept_graph import concept_graph
    from core.neural.relation_graph import relation_graph

    concept_graph.add_concept("connection_quality", "Network Connection Status")
    concept_graph.add_concept("whisper_audio_stream", "Speech Transcribing Endpoint")
    relation_graph.add_relation("connection_quality", "whisper_audio_stream", "CAUSES", causal_influence_delta=0.90)

    # Initial connection status is unverified (belief confidence 0.50)
    node_pre = neural_memory.get_node("connection_quality")
    assert node_pre.operational_state == "UNVERIFIED"

    # Ingest extremely high latency (650ms)
    success = world_model.update_telemetry_observation("network_latency_ms", 650.0)
    assert success is True

    # Host must authoritatively declare connection status as FAILED and propagate it to dependent nodes!
    node_post = neural_memory.get_node("connection_quality")
    assert node_post.belief_confidence < 0.35
    assert node_post.operational_state == "FAILED"

    # Dependent node 'whisper_audio_stream' must also have degraded confidence due to causal propagation!
    dependent_node = neural_memory.get_node("whisper_audio_stream")
    assert dependent_node.belief_confidence < 0.35
    assert dependent_node.operational_state == "FAILED"


def test_advisory_planner_warning_on_causal_degradation():
    """Verify that the Planner appends advisory failure risk warnings to candidate plans when causal components fail, without blocking."""
    # Seed causal nodes: connection_quality -> whisper_audio_stream
    from core.neural.concept_graph import concept_graph
    from core.neural.relation_graph import relation_graph

    concept_graph.add_concept("connection_quality", "Network Connection Status")
    concept_graph.add_concept("serial_diagnostic_time", "System Diagnostic and Time Check")
    relation_graph.add_relation("connection_quality", "serial_diagnostic_time", "CAUSES", causal_influence_delta=0.85)

    # Force connection_quality to FAILED state
    from core.neural.schema_reasoner import schema_reasoner
    schema_reasoner.verify_and_reconcile("connection_quality", observed_success=False)

    # Run planner generate_plan (ingests causal risks)
    graph = planner.generate_plan("prepare system and check time")
    assert graph is not None

    # Advisory check: the serial_diagnostic_time candidate plan must carry the warning, but should still be generated (not deleted/blocked)
    target_candidate = next(c for c in planner.latest_candidates if c.name == "serial_diagnostic_time")
    assert any("Advisory Causal Failure Risk:" in r for r in target_candidate.risks)


def test_graceful_fallback_on_telemetry_processing_failure():
    """Verify that any uncaught exception during telemetry processing falls back gracefully to prior state without crashing."""
    # Mock schema reasoner to throw an error during override
    with patch("core.neural.schema_reasoner.schema_reasoner.verify_and_reconcile", side_effect=Exception("Database crash")):
        success = world_model.update_telemetry_observation("network_latency_ms", 999.0)
        # Should complete and return True, falling back safely without raising uncaught exceptions
        assert success is True
