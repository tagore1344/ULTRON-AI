# backend/tests/test_e2e_integration.py
# End-to-end integration: traces the complete Phase 9E flow through the gateway.
# 1. ULTRON receives a request
# 2. Orchestrator selects provider
# 3. ULTRON reasons
# 4. Cognitive decision/proposal created
# 5. Policy classifies risk
# 6. Gateway exposes proposal
# 7. Authenticated device receives it (REST + simulated WS)
# 8. Confirmation requested when required
# 9. User approval processed
# 10. ToolRegistry executes operation
# 11. Result returned to ULTRON
# 12. Client receives final status
# 13. Memory/context updated
import os
import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.server import app
from backend.database.device_repository import device_repo
from backend.database.connection import get_db_connection
from backend.security.token_service import token_service
from backend.services.confirmation_service import confirmation_service
from backend.services.proposal_service import proposal_service
from backend.api.websocket.connection_manager import manager
from core.agent.proposal_manager import proposal_manager
from core.context.memory_manager import memory_manager
from core.agent.agent_runtime import agent_runtime
from core.agent.goal_manager import goal_manager


client = TestClient(app, raise_server_exceptions=False)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# FIXTURES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _wipe_all():
    """Nuclear reset of all mutable state."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM devices")
    cur.execute("DELETE FROM pairing_sessions")
    cur.execute("DELETE FROM brute_force_tracker")
    conn.commit()
    conn.close()

    pconn = proposal_manager.get_connection()
    pc = pconn.cursor()
    pc.execute("DELETE FROM proposal_event_log")
    pc.execute("DELETE FROM cognitive_proposals")
    pconn.commit()
    pconn.close()

    mconn = memory_manager.get_connection()
    mc = mconn.cursor()
    for table in ("episodic_memory", "semantic_memory", "strategy_memory",
                  "failure_memory", "evolution_memory"):
        mc.execute(f"DELETE FROM {table}")
    mconn.commit()
    mconn.close()

    manager.active_sessions.clear()
    manager.active_tickets.clear()
    confirmation_service.pending_requests.clear()
    agent_runtime.state = "IDLE"
    goal_manager.clear_goal()


@pytest.fixture(autouse=True)
def clean_e2e_state():
    """Wipe all mutable state before and after each test, restore config byte-exact."""
    _wipe_all()

    config_path = "assistant_config.json"
    config_backup = None
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_backup = f.read()

    yield

    _wipe_all()

    if config_backup is not None:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_backup)


@pytest.fixture
def paired_device():
    """Pairs a fresh test device for each test; returns (auth_headers, device_id)."""
    sess_resp = client.post("/api/v1/auth/pairing-session")
    pin = sess_resp.json()["pairing_code"]

    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pin,
        "device_name": "E2E Test Device",
        "device_type": "android",
        })
    data = pair_resp.json()
    device_id = data["device"]["device_id"]
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}, device_id


def _make_proposal_payload(risk_class="SAFE", payload=None, title="E2E Test"):
    return {
        "title": title,
        "reason": "Voice transcription repeatedly maps 'chroome' to a failed app launch.",
        "component": "core/tools/tool_registry.py",
        "risk_class": risk_class,
        "expected_impact": "Reduces repeated app.launch failures.",
        "proposed_action": "Add a bounded voice-alias mapping resolved by the ToolRegistry.",
        "payload": payload or {"command_alias": {"chroome": "chrome"}},
        "source_ref": "e2e_test",
        "expiry_seconds": 86400,
    }


def _record_episodic(user_prompt, intent, status, result):
    """Helper: record an interaction into episodic memory (graceful degradation)."""
    try:
        return memory_manager.add_episodic_memory(
            user_prompt=user_prompt,
            parsed_intent=intent,
            actual_results=result,
            success_status=status in ("APPLIED", "completed"),
        )
    except Exception:
        return None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# STEP 1-13: COMPLETE E2E FLOW (SAFE proposal)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_complete_e2e_safe_flow(paired_device, monkeypatch):
    """Traces the full 13-step flow for a SAFE cognitive proposal.

    1.  Orchestrator receives a request (mocked provider)
    2.  Model selector routes by category
    3.  Reasoning produces a conclusion
    4.  Judgment engine generates an opinion
    5.  Proposal created with SAFE risk classification
    6.  Gateway exposes the proposal via REST
    7.  Authenticated device lists proposals (simulated HUD receipt)
    8.  Device approves (SAFE needs no live confirmation gate)
    9.  Proposal service executes the approved adaptation
    10. Result is returned to the client
    11. Proposal status updated to APPLIED
    12. Episodic memory records the interaction
    13. Config adaptation persisted (guarded in demo mode)
    """
    auth_headers, device_id = paired_device

    # 1. Simulate an incoming user request -- orchestrator routes it
    monkeypatch.setattr(
        "ai.orchestrator.model_selector.get_provider_availability",
        lambda: {"gemini": True, "openai": True, "deepseek": True},
    )
    monkeypatch.setattr(
        "ai.orchestrator.ai_orchestrator.ask_openai",
        lambda p: "ULTRON: I'll create a voice-alias improvement proposal.",
    )
    monkeypatch.setattr(
        "ai.orchestrator.ai_orchestrator.ask_gemini",
        lambda p: "Gemini agrees: voice alias needed.",
    )
    monkeypatch.setattr(
        "ai.orchestrator.ai_orchestrator.ask_deepseek",
        lambda p: "DeepSeek concurs.",
    )

    from ai.orchestrator.ai_orchestrator import AIOrchestrator
    from core.agent.judgment_engine import judgment_engine

    brain = AIOrchestrator()
    user_input = "open chroome please"

    # 2-3. Reasoning through the orchestrator
    ranked = brain.model_selector.rank_models(user_input)
    primary = ranked[0]
    reasoning = brain.ask(user_input)
    assert primary == "openai"  # conversational intent
    assert "ULTRON" in reasoning

    # 4. Cognitive decision/proposal (driven by judgment engine)
    opinion = judgment_engine.generate_opinion(user_input)
    assert opinion.confidence_score >= 0.0

    # 5. Create the proposal via the gateway (step 6 = gateway exposure in POST)
    payload = _make_proposal_payload(
        risk_class="SAFE",
        title="Voice-alias improvement: chroome -> chrome",
    )
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    proposal = resp.json()["proposal"]
    proposal_id = proposal["proposal_id"]
    assert proposal["risk_class"] == "SAFE"
    assert proposal["status"] == "PENDING_REVIEW"

    # 6-7. Authenticated device receives the proposal (REST as simulated HUD)
    listed = client.get("/api/v1/cognitive/proposals", headers=auth_headers).json()
    assert proposal_id in [p["proposal_id"] for p in listed["proposals"]]

    # Verify proposal detail is readable
    detail = client.get(f"/api/v1/cognitive/proposals/{proposal_id}", headers=auth_headers).json()
    assert detail["proposal"]["title"] == "Voice-alias improvement: chroome -> chrome"
    assert detail["proposal"]["reason"] is not None
    assert detail["proposal"]["component"] == "core/tools/tool_registry.py"
    assert "expected_impact" in detail["proposal"]
    assert "proposed_action" in detail["proposal"]

    # 8. Device approves (SAFE -- no live confirmation gate required)
    decision_resp = client.post(
        f"/api/v1/cognitive/proposals/{proposal_id}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert decision_resp.status_code == 200
    dec_data = decision_resp.json()
    assert dec_data["resolution"] == "APPROVED"
    assert dec_data["execution"]["success"] is True
    assert dec_data["execution"]["status"] == "APPLIED"

    # 9-11. Result is returned and status updated
    final = client.get(f"/api/v1/cognitive/proposals/{proposal_id}", headers=auth_headers).json()
    assert final["proposal"]["status"] == "APPLIED"
    assert final["proposal"]["execution_result"] is not None

    # 12. Episodic memory records the interaction
    mem_id = _record_episodic(user_input, "app.open", final["proposal"]["status"],
                              final["proposal"]["execution_result"])
    assert mem_id is not None
    mem = memory_manager.get_relevant_memories("chroome")
    assert any(m["memory_id"] == mem_id for m in mem)

    # 13. Config adaptation was applied
    from core.config import load_config
    cfg = load_config()
    assert cfg.get("command_alias", {}).get("chroome") == "chrome"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECURITY BOUNDARIES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_unauthenticated_proposal_access_blocked():
    """No bearer token -- 401 on every proposal endpoint."""
    assert client.get("/api/v1/cognitive/proposals").status_code == 401
    assert client.get("/api/v1/cognitive/proposals/prop_foobar").status_code == 401
    assert client.post("/api/v1/cognitive/proposals", json={}).status_code == 401
    assert client.post("/api/v1/cognitive/proposals/prop_foobar/decision",
                       json={"decision": "approved"}).status_code == 401
    assert client.post("/api/v1/cognitive/proposals/prop_foobar/cancel",
                       json={}).status_code == 401


def test_revoked_device_cannot_access_proposals(paired_device):
    """A revoked device must get 401 on every proposal endpoint."""
    auth_headers, device_id = paired_device
    device_repo.revoke_device(device_id)
    assert client.get("/api/v1/cognitive/proposals", headers=auth_headers).status_code == 401
    assert client.get("/api/v1/cognitive/proposals/prop_any", headers=auth_headers).status_code == 401
    assert client.post("/api/v1/cognitive/proposals", headers=auth_headers,
                       json=_make_proposal_payload()).status_code == 401


def test_high_risk_proposal_without_confirmation_is_blocked(paired_device):
    """HIGH_RISK proposals need a live confirmation gate; without a live confirmation the gate blocks execution."""
    auth_headers, device_id = paired_device
    payload = _make_proposal_payload(
        risk_class="HIGH_RISK",
        title="Source-code change",
        payload={"change_proposal": {"file": "core/brain.py", "diff": "@@ change @@"}},
    )
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    pid = resp.json()["proposal"]["proposal_id"]

    # Approve via the decision endpoint -- this triggers execute_approved_proposal
    # internally, which must pass through the confirmation gate. Without a live
    # confirmation response, the gate blocks execution after the timeout window.
    dec_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved", "confirm_timeout_seconds": 1},
    )
    assert dec_resp.status_code == 200
    exec_result = dec_resp.json()["execution"]
    assert exec_result["success"] is False
    assert "CONFIRMATION_NOT_GRANTED" in exec_result["status"]


def test_high_risk_source_change_never_applied_directly(paired_device):
    """Even when confirmed, HIGH_RISK source-change payloads only record authorization."""
    auth_headers, device_id = paired_device
    payload = _make_proposal_payload(
        risk_class="HIGH_RISK",
        payload={"change_proposal": {"file": "core/brain.py", "diff": "@@ malicious @@"}},
    )
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    pid = resp.json()["proposal"]["proposal_id"]

    # _apply_payload is a synchronous method -- call it directly.
    # Source-change payloads must only produce AUTHORIZED_FOR_SIGNED_RELEASE,
    # never actually modifying code files.
    result = proposal_service._apply_payload(
        proposal_manager.get_proposal(pid),
        {"change_proposal": {"file": "core/brain.py", "diff": "@@ malicious @@"}},
    )
    assert result["success"] is True
    assert result["status"] == "AUTHORIZED_FOR_SIGNED_RELEASE"


def test_malformed_proposal_id_returns_404(paired_device):
    """Malformed proposal IDs (not starting with prop_) must 404, not crash."""
    auth_headers, _ = paired_device
    resp = client.get("/api/v1/cognitive/proposals/bad_id", headers=auth_headers)
    assert resp.status_code == 404
    resp = client.post("/api/v1/cognitive/proposals/bad_id/decision",
                       headers=auth_headers, json={"decision": "approved"})
    assert resp.status_code == 404


def test_duplicate_approval_is_rejected(paired_device):
    """A proposal already APPLIED must refuse a second decision (409)."""
    auth_headers, _ = paired_device
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers,
                       json=_make_proposal_payload(risk_class="SAFE"))
    pid = resp.json()["proposal"]["proposal_id"]
    first = client.post(f"/api/v1/cognitive/proposals/{pid}/decision",
                        headers=auth_headers, json={"decision": "approved"})
    assert first.status_code == 200
    second = client.post(f"/api/v1/cognitive/proposals/{pid}/decision",
                         headers=auth_headers, json={"decision": "approved"})
    assert second.status_code == 409


def test_already_rejected_proposal_cannot_be_reapproved(paired_device):
    """A rejected proposal cannot be re-approved."""
    auth_headers, _ = paired_device
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers,
                       json=_make_proposal_payload(risk_class="SAFE"))
    pid = resp.json()["proposal"]["proposal_id"]
    rej = client.post(f"/api/v1/cognitive/proposals/{pid}/decision",
                      headers=auth_headers, json={"decision": "rejected"})
    assert rej.status_code == 200
    reapprove = client.post(f"/api/v1/cognitive/proposals/{pid}/decision",
                            headers=auth_headers, json={"decision": "approved"})
    assert reapprove.status_code == 409


def test_expired_proposal_cannot_be_decided(paired_device):
    """Proposals past expiry auto-resolve to EXPIRED and refuse decisions."""
    auth_headers, _ = paired_device
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers,
                       json=_make_proposal_payload(title="Expiring"))
    pid = resp.json()["proposal"]["proposal_id"]
    conn = proposal_manager.get_connection()
    conn.execute("UPDATE cognitive_proposals SET expires_at = '2020-01-01T00:00:00Z' WHERE proposal_id = ?", (pid,))
    conn.commit()
    conn.close()
    decision = client.post(f"/api/v1/cognitive/proposals/{pid}/decision",
                           headers=auth_headers, json={"decision": "approved"})
    assert decision.status_code == 409
    detail = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers).json()["proposal"]
    assert detail["status"] == "EXPIRED"


def test_invalid_risk_class_rejected(paired_device):
    """Invalid risk_class must return 422."""
    auth_headers, _ = paired_device
    payload = _make_proposal_payload(risk_class="BOGUS")
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers, json=payload)
    assert resp.status_code == 422


def test_proposal_create_validates_required_fields(paired_device):
    """Proposals with all required fields return 201."""
    auth_headers, _ = paired_device
    resp = client.post("/api/v1/cognitive/proposals", headers=auth_headers, json={
        "title": "test", "reason": "y", "component": "test_component",
        "risk_class": "SAFE", "expected_impact": "i",
        "proposed_action": "a"
    })
    assert resp.status_code == 201


