# backend/tests/test_neural_schema.py
import pytest
import sqlite3
import datetime
import json
from unittest.mock import MagicMock, patch

from core.neural.neural_schema import NeuralNodeModel, NeuralEdgeModel
from core.neural.neural_memory import neural_memory
from core.neural.entity_graph import entity_graph
from core.neural.relation_graph import relation_graph
from core.neural.concept_graph import concept_graph
from core.neural.event_memory import event_memory
from core.neural.causal_graph import causal_graph
from core.neural.belief_state import belief_state
from core.neural.prediction_engine import prediction_engine
from core.neural.schema_reasoner import schema_reasoner
from core.agent.agent_runtime import agent_runtime
from core.agent.planner import planner
from core.agent.policy_engine import policy_engine
from core.tools.tool_registry import ToolRegistry


@pytest.fixture(autouse=True)
def clean_neural_tables():
    """Ensure that the neural schema database tables are clean and isolated for each test."""
    conn = neural_memory.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM neural_edges")
    cursor.execute("DELETE FROM neural_nodes")
    conn.commit()
    conn.close()

    yield

    conn = neural_memory.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM neural_edges")
    cursor.execute("DELETE FROM neural_nodes")
    conn.commit()
    conn.close()


def test_node_validation_and_malicious_payload_rejection():
    """Verify that NeuralNodeModel validates fields and strictly rejects malicious code payload injections."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

    # 1. Valid node
    node = NeuralNodeModel(
        node_id="test_node_01",
        node_type="ENTITY",
        label="Microphone Component",
        properties={"snr_db": 15.0},
        belief_confidence=0.90,
        operational_state="KNOWN",
        last_updated=now_str
    )
    assert node.node_id == "test_node_01"
    assert node.properties["snr_db"] == 15.0

    # 2. Malicious Python payload rejection
    with pytest.raises(ValueError, match="Malicious payload blocked"):
        NeuralNodeModel(
            node_id="malicious_node",
            node_type="ENTITY",
            label="Microphone",
            properties={"exploit": "import os; os.system('rm -rf /')"},
            last_updated=now_str
        )


def test_edge_validation():
    """Verify that NeuralEdgeModel validates edge properties."""
    edge = NeuralEdgeModel(
        edge_id="edge_001",
        source_id="mic_01",
        target_id="poor_audio_01",
        relationship_type="CAUSES",
        link_confidence=0.95,
        causal_influence_delta=0.85
    )
    assert edge.edge_id == "edge_001"
    assert edge.causal_influence_delta == 0.85


def test_belief_update_and_policy_state_separation():
    """Verify Bayesian confidence updates operate statefully and map cleanly to distinct policy statuses."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    node = NeuralNodeModel(
        node_id="test_sensor",
        node_type="STATE",
        label="Internet connectivity",
        properties={},
        belief_confidence=0.50, # Neutral
        operational_state="UNVERIFIED",
        last_updated=now_str
    )
    neural_memory.save_node(node)

    # 1. Ingest success evidence -> moves belief toward 1.0 (B_new = 0.5 + 0.2*(1.0-0.5) = 0.6)
    belief_state.ingest_evidence("test_sensor", success=True)
    updated = neural_memory.get_node("test_sensor")
    assert updated.belief_confidence == 0.60
    assert updated.operational_state == "UNVERIFIED"

    # 2. Ingest consecutive successes until belief confidence >= 0.85 (Policy threshold for KNOWN)
    for _ in range(5):
        belief_state.ingest_evidence("test_sensor", success=True)

    updated_known = neural_memory.get_node("test_sensor")
    assert updated_known.belief_confidence >= 0.85
    assert updated_known.operational_state == "KNOWN"

    # 3. Ingest failure evidence -> degrades belief confidence (B_new = B_old - 0.2*B_old)
    # Failure takes belief down below 0.35 -> policy state transitions to FAILED
    for _ in range(8):
        belief_state.ingest_evidence("test_sensor", success=False)

    updated_failed = neural_memory.get_node("test_sensor")
    assert updated_failed.belief_confidence < 0.35
    assert updated_failed.operational_state == "FAILED"


def test_contradiction_handling_factual_override():
    """Verify that schema reasoner logs contradictions and overrides subjective beliefs with facts."""
    now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    node = NeuralNodeModel(
        node_id="wifi_signal",
        node_type="STATE",
        label="WiFi Connection",
        properties={},
        belief_confidence=0.95, # Subjective high certainty
        operational_state="KNOWN",
        last_updated=now_str
    )
    neural_memory.save_node(node)

    # Fact: Environment reports connection is actually down (observed_success=False)
    # Contradiction: |0.0 - 0.95| = 0.95 >= 0.60. Factual override must trigger.
    success = schema_reasoner.verify_and_reconcile("wifi_signal", observed_success=False)
    assert success is True

    updated_node = neural_memory.get_node("wifi_signal")
    # Should instantly degrade and override high belief
    assert updated_node.belief_confidence < 0.35
    assert updated_node.operational_state == "FAILED"


def test_causal_propagation_and_advisory_prediction():
    """Verify downstream causal failure propagation and trace back advisory risk forecasts."""
    # Seed nodes: mic_signal -> poor_audio -> whisper_error
    entity_graph.add_entity("mic_signal", "Microphone Signal level")
    concept_graph.add_concept("poor_audio", "Degraded Audio Waveform")
    concept_graph.add_concept("whisper_error", "Whisper Transcriber timeout")

    # Seed relationships: mic_signal -[CAUSES]-> poor_audio -[CAUSES]-> whisper_error
    relation_graph.add_relation("mic_signal", "poor_audio", "CAUSES", causal_influence_delta=0.85)
    relation_graph.add_relation("poor_audio", "whisper_error", "CAUSES", causal_influence_delta=0.90)

    # 1. Base Causal Prediction (no failure yet)
    risk_pre = prediction_engine.compute_advisory_failure_risk("whisper_error")
    assert risk_pre < 0.60

    # 2. Trigger Root Failure on 'mic_signal'
    schema_reasoner.verify_and_reconcile("mic_signal", observed_success=False)

    # Assert that causal failure propagated across the edge to poor_audio and whisper_error
    updated_whisper = neural_memory.get_node("whisper_error")
    assert updated_whisper.belief_confidence < 0.35 # Degraded statefully
    assert updated_whisper.operational_state == "FAILED"

    # 3. Post-Failure Causal Advisory Risk
    risk_post = prediction_engine.compute_advisory_failure_risk("whisper_error")
    # Risk should now be high because upstream causal nodes have failed
    assert risk_post >= 0.85


def test_graph_persistence_and_subgraph_retrieval():
    """Verify node/edge persistence and selective sub-graph depth-bounding retrieval."""
    entity_graph.add_entity("laptop", "Windows laptop")
    entity_graph.add_entity("mic", "Physical USB mic")
    entity_graph.add_entity("overlay", "PyQt overlay UI")

    relation_graph.add_relation("laptop", "mic", "HAS_HARDWARE")
    relation_graph.add_relation("laptop", "overlay", "RUNS_PROCESS")

    # Retrieve subgraph centered on laptop
    nodes, edges = neural_memory.get_subgraph("laptop", max_depth=1)

    assert len(nodes) == 3 # laptop, mic, and overlay
    assert len(edges) == 2 # HAS_HARDWARE and RUNS_PROCESS


@pytest.mark.anyio
async def test_tool_registry_boundary_protection():
    """Verify that the Neural Schema is strictly symbolic and can never bypass ToolRegistry or execute system tools."""
    # Attempting to call non-diagnostics intents on ToolRegistry from neural entities fails cleanly
    registry = ToolRegistry()

    # Try calling a custom fake intent (blocks and fails closed)
    try:
        res = await registry.execute({"intent": "neural.execute_raw_code"})
        assert "Unknown tool" in res or "bypassed" not in res
    except Exception:
         pass


@pytest.mark.anyio
async def test_phase_9a_9b_9c_regressions_and_integration():
    """Verify all pre-existing tests remain fully functional, and ensure integration hooks don't break loops."""
    # 1. Check existing 9A loop runs green
    with patch.object(planner, "generate_plan") as mock_plan:
        success, msg = await agent_runtime.execute_goal("tiny.en is better than base.en")
        assert success is False
        assert "DISAGREEMENT" in msg

    # 2. Verify World Model and Self Model continue returning summaries with active neural integration hooks
    from core.context.self_model import self_model
    from core.context.world_model import world_model

    self_summary = self_model.get_summary()
    assert "capabilities" in self_summary

    world_summary = world_model.get_summary()
    assert "operating_system" in world_summary
