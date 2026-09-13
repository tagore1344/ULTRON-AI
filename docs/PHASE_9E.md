# ULTRON-AI Phase 9E — Cognitive Proposals on the Mobile HUD

**Status:** Implemented
**Security Boundary:** Unchanged — proposals never bypass the existing policy/confirmation stack.

---

## 1. Purpose

Phase 9E closes the loop between ULTRON's independent reasoning layers and the
human operator. When a cognitive subsystem (judgment engine, evolution
hypothesis engine, agent runtime) concludes that a change is advisable but the
action crosses a policy boundary, it now surfaces a **Cognitive Change-Proposal**
that the operator can review, approve, reject, or cancel from the mobile HUD.

## 2. Data Flow

```
ULTRON Cognitive Engine (judgment / evolution / agent runtime)
        │  create_proposal(...)
        ▼
ProposalManager (SQLite: backend/data/ultron_context.db
                 tables: cognitive_proposals + proposal_event_log)
        │  broadcast PROPOSAL_CREATED (WebSocket, all paired HUDs)
        ▼
FastAPI Gateway  /api/v1/cognitive/proposals[...]   (Bearer auth + scopes)
        │
        ▼
Flutter HUD "REVIEW" tab  (risk badges, full detail, approve/reject/cancel)
        │  POST .../decision {"decision": "approved"|"rejected"}
        ▼
Policy Enforcement:
  SAFE                  -> applied immediately (assistant_config.json adapters)
  CONFIRMATION_REQUIRED -> existing CONFIRMATION_REQUEST window (30s default)
  HIGH_RISK             -> existing CONFIRMATION_REQUEST window; source-change
                           payloads are NEVER applied directly — approval is
                           recorded as a SHA-256-sealed authorization event in
                           proposal_event_log, feeding the human-signed release
                           pipeline (core/update).
        │
        ▼
PROPOSAL_EXECUTION_RESULT broadcast + status APPLIED / APPLY_FAILED
```

## 3. REST API (all require Bearer auth from the existing pairing system)

| Method | Path | Scope | Purpose |
|--------|------|-------|---------|
| GET | `/cognitive/proposals` | `system_status` | List pending proposals (`?resolved=true` includes resolved) |
| GET | `/cognitive/proposals/{id}` | `system_status` | Full sanitized detail packet |
| POST | `/cognitive/proposals` | `safe_commands` | Create a proposal from an authorized source |
| POST | `/cognitive/proposals/{id}/decision` | `safe_commands` | `approved` / `rejected` (+ optional note) |
| POST | `/cognitive/proposals/{id}/cancel` | `safe_commands` | Cancel a pending proposal |

Decision endpoint behavior:
* Unknown/malformed IDs → `404`; already-resolved proposals → `409` (replay protection).
* Approved `CONFIRMATION_REQUIRED`/`HIGH_RISK` proposals additionally require the
  live `CONFIRMATION_REQUEST`/`CONFIRMATION_RESPONSE` WebSocket handshake
  (re-using `confirmation_service` and the WS ticket mechanism — no second auth system).

## 4. WebSocket Events (new `EventType` values)

`PROPOSAL_CREATED`, `PROPOSAL_RESOLVED`, `PROPOSAL_EXPIRED`, `PROPOSAL_EXECUTION_RESULT`

Delivery is best-effort broadcast to active sessions. Clients recover missed
events via the REST ledger on reconnect (`ProposalController` re-fetches when
`ConnectionController` reports connected). No polling loop is required.

## 5. Proposal Lifecycle States

`PENDING_REVIEW → APPROVED | REJECTED | CANCELLED | EXPIRED`
`APPROVED → APPLIED | APPLY_FAILED`

Every transition writes an event row to `proposal_event_log` (actor, detail,
payload hash) providing a tamper-evident audit trail.

## 6. SAFE Application Adapters

Approved SAFE adaptations are persisted into `assistant_config.json`:
* `command_alias` → merged into `voice_aliases` (consumed by `core/tools/tool_registry.py`)
* `memory_retrieval_weight` → `memory_retrieval_weight`
* `model_routing` → `model_routing`

`change_proposal` payloads are never file-applied by the gateway (see §2).

## 7. Mobile HUD

* New `REVIEW` tab (`features/proposals/`): list, detail sheet, risk-colored
  badges — SAFE (green), CONFIRM (amber), HIGH_RISK (red) — and controls.
* HIGH_RISK approvals additionally require an explicit on-device reinforcement
  dialog (the gateway's live confirmation gate still applies regardless).
* Tests: `mobile/ultron_mobile/test/proposal_model_test.dart`.

## 8. Testing

`backend/tests/test_phase9e.py` (14 cases) covers the full flow and negatives:
unauthenticated access, missing scopes, malformed/unknown IDs, duplicate and
invalid decisions, already-resolved lockouts, expired proposals, HIGH_RISK
blocked without live confirmation, HIGH_RISK authorized through it, rejection
at the gate, cancellation, WS-reconnect recovery, and the evolution bridge.
