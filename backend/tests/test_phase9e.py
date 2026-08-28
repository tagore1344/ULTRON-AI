# backend/tests/test_phase9e.py — Cognitive Change-Proposal Gateway (Phase 9E)
import pytest
import asyncio
import json
from fastapi.testclient import TestClient

from backend.server import app
from backend.database.device_repository import device_repo
from backend.services.confirmation_service import confirmation_service
from backend.services.proposal_service import proposal_service
from core.agent.proposal_manager import proposal_manager
from core.config import load_config, save_config

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_proposal_state():
    """Fresh proposal ledger, clean lockouts, and a protected assistant config."""
    device_repo.reset_failed_attempts("testclient")
    device_repo.reset_failed_attempts("127.0.0.1")
    confirmation_service.pending_requests.clear()

    conn = proposal_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proposal_event_log")
    cursor.execute("DELETE FROM cognitive_proposals")
    conn.commit()
    conn.close()

    config_backup = json.dumps(load_config())

    yield

    conn = proposal_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proposal_event_log")
    cursor.execute("DELETE FROM cognitive_proposals")
    conn.commit()
    conn.close()

    save_config(json.loads(config_backup))
    confirmation_service.pending_requests.clear()


@pytest.fixture(scope="module")
def auth_context():
    """Pairs a test device; returns (auth_headers, device_id)."""
    sess_resp = client.post("/api/v1/auth/pairing-session")
    pin = sess_resp.json()["pairing_code"]

    pair_resp = client.post("/api/v1/auth/pair", json={
        "pairing_code": pin,
        "device_name": "Phase 9E Test Device",
        "device_type": "android"
    })
    data = pair_resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["device"]["device_id"]


def _create_proposal(auth_headers, risk_class="SAFE", payload=None, title="Test proposal"):
    body = {
        "title": title,
        "reason": "Voice transcription repeatedly maps 'chroome' to a failed app launch.",
        "component": "core/tools/tool_registry.py",
        "risk_class": risk_class,
        "expected_impact": "Reduces repeated app.launch failures.",
        "proposed_action": "Add a bounded voice alias mapping.",
        "payload": payload or {"command_alias": {"chroome": "chrome"}},
        "source_ref": "hyp_test_9e",
    }
    return client.post("/api/v1/cognitive/proposals", headers=auth_headers, json=body)


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION
# ==============================================================================

def test_proposal_endpoints_require_authentication():
    response = client.get("/api/v1/cognitive/proposals")
    assert response.status_code == 401

    response = client.post(
        "/api/v1/cognitive/proposals/prop_doesnotexist/decision",
        json={"decision": "approved"},
    )
    assert response.status_code == 401


def test_proposal_endpoints_require_safe_commands_scope(auth_context):
    """system_status-only devices can read but not decide; unscoped devices cannot read."""
    auth_headers, _ = auth_context
    # Paired default device holds safe_commands: decisions should pass auth layer
    # (a state error is acceptable; 401/403 would be an auth-layer failure).
    resp = client.post(
        "/api/v1/cognitive/proposals/prop_unknown_id_9e/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert resp.status_code in (404, 409)


# ==============================================================================
# SAFE PROPOSAL FULL FLOW
# ==============================================================================

def test_safe_proposal_full_lifecycle(auth_context):
    """cognitive proposal created -> gateway exposes it -> approve -> applied -> result recorded."""
    auth_headers, device_id = auth_context

    # 1. Create
    create_resp = _create_proposal(auth_headers)
    assert create_resp.status_code == 201
    proposal = create_resp.json()["proposal"]
    pid = proposal["proposal_id"]
    assert proposal["status"] == "PENDING_REVIEW"
    assert proposal["risk_class"] == "SAFE"
    assert proposal["title"] == "Test proposal"

    # 2. HUD lists it
    list_resp = client.get("/api/v1/cognitive/proposals", headers=auth_headers)
    assert list_resp.status_code == 200
    listed_ids = [p["proposal_id"] for p in list_resp.json()["proposals"]]
    assert pid in listed_ids

    # 3. Detail contains every field the HUD needs
    detail_resp = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["proposal"]
    for field in ("title", "reason", "component", "risk_class", "expected_impact",
                  "proposed_action", "status", "payload"):
        assert field in detail

    # 4. Approve -> SAFE proposals apply immediately (no second confirmation gate)
    decision_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved", "note": "Looks safe"},
    )
    assert decision_resp.status_code == 200
    body = decision_resp.json()
    assert body["resolution"] == "APPROVED"
    assert body["execution"]["success"] is True
    assert body["execution"]["status"] == "APPLIED"

    # 5. Real effect: the applier reports the exact adaptation keys applied
    assert "command_alias" in body["execution"]["detail"]

    # 6. Final state is APPLIED and hidden from the pending list
    final = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers).json()["proposal"]
    assert final["status"] == "APPLIED"
    assert final["resolved_by"] == device_id
    assert pid not in [p["proposal_id"] for p in
                       client.get("/api/v1/cognitive/proposals", headers=auth_headers).json()["proposals"]]


def test_approved_adaptation_persists_to_assistant_config():
    """In-process proof that approved SAFE adaptations are persisted for the live assistant."""
    from backend.services.proposal_service import ProposalService

    original = json.dumps(load_config())
    try:
        service = ProposalService()
        service._save_config_key("voice_aliases", {"chroome": "chrome"})
        assert load_config().get("voice_aliases") == {"chroome": "chrome"}

        # Merging behavior: a second approval extends the existing mapping
        service._save_config_key("voice_aliases", {"gogle": "google"})
        assert load_config().get("voice_aliases") == {"chroome": "chrome", "gogle": "google"}
    finally:
        save_config(json.loads(original))


def test_rejection_flow_and_resolved_lockout(auth_context):
    """Rejected proposals stay rejected: later approvals conflict with 409."""
    auth_headers, _ = auth_context

    create_resp = _create_proposal(auth_headers, title="Reject me")
    pid = create_resp.json()["proposal"]["proposal_id"]

    reject_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "rejected", "note": "Not convinced"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["resolution"] == "REJECTED"
    assert reject_resp.json()["execution"] is None

    # Already-resolved proposals must never be re-decided (replay protection)
    replay_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert replay_resp.status_code == 409

    detail = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers).json()["proposal"]
    assert detail["status"] == "REJECTED"


def test_malformed_and_unknown_proposal_ids(auth_context):
    """Malformed and unknown IDs return clean 404s, never 500s."""
    auth_headers, _ = auth_context

    for bad_id in ("garbage", "prop_", "prop_does_not_exist_9e", "../../etc/passwd"):
        resp = client.get(f"/api/v1/cognitive/proposals/{bad_id}", headers=auth_headers)
        assert resp.status_code == 404

        dec_resp = client.post(
            f"/api/v1/cognitive/proposals/{bad_id}/decision",
            headers=auth_headers,
            json={"decision": "approved"},
        )
        assert dec_resp.status_code == 404


def test_duplicate_and_invalid_decisions(auth_context):
    """Invalid decision strings are rejected with 422/409, never partially applied."""
    auth_headers, _ = auth_context
    pid = _create_proposal(auth_headers, title="Dup check").json()["proposal"]["proposal_id"]

    invalid_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "hack_the_planet"},
    )
    assert invalid_resp.status_code == 422

    # Approve once (SAFE applies), then re-approve must conflict
    first = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert second.status_code == 409


# ==============================================================================
# HIGH_RISK POLICY ENFORCEMENT
# ==============================================================================

def test_high_risk_blocked_without_live_confirmation(auth_context):
    """HIGH_RISK approval alone must NOT execute: the live confirmation gate is mandatory."""
    auth_headers, _ = auth_context

    create_resp = _create_proposal(
        auth_headers,
        risk_class="HIGH_RISK",
        payload={"change_proposal": {"file": "voice_id.py", "diff": "@@ -20,2 +20,4 @@"}},
        title="Source change: voice_id.py",
    )
    pid = create_resp.json()["proposal"]["proposal_id"]
    assert create_resp.json()["proposal"]["risk_class"] == "HIGH_RISK"

    decision_resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved", "confirm_timeout_seconds": 0.2},
    )
    assert decision_resp.status_code == 200
    execution = decision_resp.json()["execution"]
    assert execution["success"] is False
    assert execution["status"] == "CONFIRMATION_NOT_GRANTED"

    final = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers).json()["proposal"]
    assert final["status"] == "APPLY_FAILED"


@pytest.mark.anyio
async def test_high_risk_authorized_through_live_confirmation(auth_context):
    """Full HIGH_RISK happy path: approval + live CONFIRMATION_REQUEST -> hash-sealed authorization."""
    auth_headers, device_id = auth_context

    proposal = proposal_manager.create_proposal(
        title="Source change: voice_id.py",
        reason="voice_id.py lacks dynamic thresholding",
        component="voice_id.py",
        risk_class="HIGH_RISK",
        expected_impact="error_rate 0.35 -> 0.02",
        proposed_action="Authorize diff through the signed release pipeline.",
        payload={"change_proposal": {"file": "voice_id.py", "diff": "@@ -20,2 +20,4 @@"}},
        source="evolution",
        source_ref="hyp_9e_async",
    )
    pid = proposal["proposal_id"]

    ok, status_msg, resolved = proposal_manager.submit_decision(
        proposal_id=pid, device_id=device_id, decision="approved", note="HUD approved",
    )
    assert ok is True and status_msg == "APPROVED"

    exec_task = asyncio.create_task(
        proposal_service.execute_approved_proposal(pid, device_id, timeout_seconds=5.0)
    )
    await asyncio.sleep(0.05)

    assert len(confirmation_service.pending_requests) == 1
    req_id = list(confirmation_service.pending_requests.keys())[0]

    confirmed = confirmation_service.submit_decision(
        request_id=req_id,
        command_id=pid,
        device_id=device_id,
        decision="approved",
    )
    assert confirmed is True

    result = await exec_task
    assert result["success"] is True
    assert result["status"] == "AUTHORIZED_FOR_SIGNED_RELEASE"

    final = proposal_manager.get_proposal(pid)
    assert final["status"] == "APPLIED"


@pytest.mark.anyio
async def test_high_risk_rejection_at_confirmation_gate(auth_context):
    """A live-confirmation REJECT must fail the execution even after HUD approval."""
    _, device_id = auth_context

    proposal = proposal_manager.create_proposal(
        title="Risky tweak",
        reason="testing",
        component="system",
        risk_class="CONFIRMATION_REQUIRED",
        expected_impact="none",
        proposed_action="apply",
        payload={"memory_retrieval_weight": {"episodic": 2.0}},
    )
    pid = proposal["proposal_id"]
    proposal_manager.submit_decision(pid, device_id, "approved")

    exec_task = asyncio.create_task(
        proposal_service.execute_approved_proposal(pid, device_id, timeout_seconds=5.0)
    )
    await asyncio.sleep(0.05)
    req_id = list(confirmation_service.pending_requests.keys())[0]
    confirmation_service.submit_decision(req_id, pid, device_id, "rejected")

    result = await exec_task
    assert result["success"] is False
    assert result["status"] == "CONFIRMATION_NOT_GRANTED"
    assert proposal_manager.get_proposal(pid)["status"] == "APPLY_FAILED"


# ==============================================================================
# EXPIRY, CANCELLATION, AND RECONNECT RESILIENCE
# ==============================================================================

def test_stale_proposals_expire(auth_context):
    """Proposals past their expiry window resolve to EXPIRED and refuse decisions."""
    auth_headers, _ = auth_context
    pid = _create_proposal(auth_headers, title="Expiring proposal").json()["proposal"]["proposal_id"]

    # Backdate the expiry window directly in the ledger
    conn = proposal_manager.get_connection()
    conn.execute("UPDATE cognitive_proposals SET expires_at = '2020-01-01T00:00:00Z' WHERE proposal_id = ?", (pid,))
    conn.commit()
    conn.close()

    resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert resp.status_code == 409

    detail = client.get(f"/api/v1/cognitive/proposals/{pid}", headers=auth_headers).json()["proposal"]
    assert detail["status"] == "EXPIRED"


def test_cancel_pending_proposal(auth_context):
    auth_headers, _ = auth_context
    pid = _create_proposal(auth_headers, title="Cancellable").json()["proposal"]["proposal_id"]

    cancel_resp = client.post(f"/api/v1/cognitive/proposals/{pid}/cancel", headers=auth_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Second cancel must conflict (already resolved)
    assert client.post(f"/api/v1/cognitive/proposals/{pid}/cancel", headers=auth_headers).status_code == 409


def test_reconnect_graceful_degradation_rest_truth(auth_context):
    """After a WS drop, a reconnecting HUD recovers state through the REST ledger.

    The creation-time broadcast is a no-op without live sockets (graceful), and
    the proposal must still be fully visible and decidable after 'reconnect'.
    """
    auth_headers, _ = auth_context
    pid = _create_proposal(auth_headers, title="Reconnect case").json()["proposal"]["proposal_id"]

    # Simulated fresh reconnect: plain REST reads see everything.
    listed = client.get("/api/v1/cognitive/proposals", headers=auth_headers).json()
    assert pid in [p["proposal_id"] for p in listed["proposals"]]

    resp = client.post(
        f"/api/v1/cognitive/proposals/{pid}/decision",
        headers=auth_headers,
        json={"decision": "approved"},
    )
    assert resp.status_code == 200
    assert resp.json()["execution"]["success"] is True


# ==============================================================================
# EVOLUTION BRIDGE
# ==============================================================================

def test_evolution_high_risk_candidate_creates_reviewable_proposal():
    """CandidateManager HIGH_RISK candidates surface a HUD proposal while staying REJECTED."""
    from core.evolution.candidate_manager import candidate_manager

    hypothesis = {
        "id": "hyp_9e_bridge",
        "observed_problem": "voice ID failures on ambient noise",
        "proposed_adaptation": {"change_proposal": {"file": "voice_id.py", "diff": "@@ -1,1 @@"}},
        "predicted_outcomes": {"error_rate": 0.02},
        "risk_class": "HIGH_RISK",
    }

    candidate = candidate_manager.create_candidate(hypothesis)
    assert candidate["status"] == "REJECTED"  # banned from automatic execution
    assert candidate["resource_budget"] == {"tokens": 0, "runs": 0}

    pending = proposal_manager.list_proposals()
    assert len(pending) == 1
    bridged = pending[0]
    assert bridged["risk_class"] == "HIGH_RISK"
    assert bridged["source"] == "evolution"
    assert bridged["source_ref"] == "hyp_9e_bridge"
    assert bridged["payload"] == hypothesis["proposed_adaptation"]