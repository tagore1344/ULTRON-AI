# core/agent/proposal_manager.py — Phase 9E Cognitive Change-Proposal Lifecycle
import os
import json
import uuid
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")

# Risk taxonomy — mirrors the gateway command classification (docs/ARCHITECTURE.md §4.2)
RISK_SAFE = "SAFE"
RISK_CONFIRM = "CONFIRMATION_REQUIRED"
RISK_HIGH = "HIGH_RISK"
VALID_RISK_CLASSES = (RISK_SAFE, RISK_CONFIRM, RISK_HIGH)

PROPOSAL_STATUSES = (
    "PENDING_REVIEW", "AWAITING_APPROVAL", "APPROVED", "REJECTED",
    "CANCELLED", "EXPIRED", "APPLIED", "APPLY_FAILED"
)


class ProposalManager:
    """Manages the full lifecycle of cognitive change-proposals.

    Proposals are created by ULTRON's cognitive layers (judgment engine,
    evolution/hypothesis engine) whenever a suggested adaptation crosses a
    policy boundary requiring human authorization. Persisted in SQLite so
    proposals survive gateway restarts and can be re-hydrated by HUD clients.
    """

    def __init__(self):
        self.initialize_database()

    # ==============================================================================
    # PERSISTENCE
    # ==============================================================================

    def get_connection(self) -> sqlite3.Connection:
        """Returns thread-safe connection to the shared context database."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Initializes the proposal ledger schema idempotently."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_proposals (
                proposal_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                reason TEXT NOT NULL,
                component TEXT NOT NULL,
                risk_class TEXT NOT NULL CHECK (risk_class IN ('SAFE', 'CONFIRMATION_REQUIRED', 'HIGH_RISK')),
                expected_impact TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                payload TEXT,
                source TEXT,
                source_ref TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                resolution_note TEXT,
                execution_result TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proposal_event_log (
                event_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL REFERENCES cognitive_proposals(proposal_id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                payload_hash TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    # ==============================================================================
    # CREATION
    # ==============================================================================

    def create_proposal(
        self,
        title: str,
        reason: str,
        component: str,
        risk_class: str,
        expected_impact: str,
        proposed_action: str,
        payload: Optional[Dict[str, Any]] = None,
        source: str = "cognitive",
        source_ref: Optional[str] = None,
        expiry_seconds: int = 86400
    ) -> Optional[Dict[str, Any]]:
        """Registers a new change-proposal awaiting human review. Returns the client-safe dict."""
        if risk_class not in VALID_RISK_CLASSES:
            logger.error("Proposal rejected: invalid risk class '%s'.", risk_class)
            return None

        title = str(title) if title is not None else ""
        if not title.strip():
            logger.error("Proposal rejected: title is required.")
            return None

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cognitive_proposals (
                proposal_id, title, reason, component, risk_class, expected_impact,
                proposed_action, payload, source, source_ref, status,
                created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id,
                title.strip(),
                str(reason or "").strip(),
                str(component or "").strip(),
                risk_class,
                str(expected_impact or "").strip(),
                str(proposed_action or "").strip(),
                json.dumps(payload) if payload else None,
                source,
                source_ref,
                "PENDING_REVIEW",
                now.isoformat() + "Z",
                (now + datetime.timedelta(seconds=expiry_seconds)).isoformat() + "Z" if expiry_seconds else None,
            )
        )

        cursor.execute(
            """
            INSERT INTO proposal_event_log (event_id, proposal_id, event_type, actor, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"pev_{uuid.uuid4().hex[:12]}",
                proposal_id,
                "PROPOSAL_CREATED",
                source,
                source_ref or title,
                now.isoformat() + "Z",
            )
        )

        conn.commit()
        conn.close()
        logger.info("Cognitive proposal created: %s [%s] risk=%s", proposal_id, title, risk_class)

        return self.get_proposal(proposal_id)

    # ==============================================================================
    # RETRIEVAL
    # ==============================================================================

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single proposal as a client-safe dict, or None."""
        if not proposal_id or not isinstance(proposal_id, str) or not proposal_id.startswith("prop_"):
            return None

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cognitive_proposals WHERE proposal_id = ?", (proposal_id,))
        row = cursor.fetchone()
        conn.close()
        return self._to_client_dict(row) if row else None

    def list_proposals(self, status: Optional[str] = None, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Lists proposals, newest first. Resolved ones are hidden unless requested."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM cognitive_proposals WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        elif include_resolved:
            cursor.execute("SELECT * FROM cognitive_proposals ORDER BY created_at DESC")
        else:
            cursor.execute(
                """SELECT * FROM cognitive_proposals
                   WHERE status IN ('PENDING_REVIEW', 'AWAITING_APPROVAL')
                   ORDER BY created_at DESC"""
            )

        rows = cursor.fetchall()
        conn.close()
        return [self._to_client_dict(r) for r in rows]

    def _to_client_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Converts a DB row into the sanitized client-facing proposal envelope."""
        data = dict(row)
        if data.get("payload"):
            try:
                data["payload"] = json.loads(data["payload"])
            except Exception:
                data["payload"] = None
        return data

    # ==============================================================================
    # DECISIONS (Human Authorization)
    # ==============================================================================

    def submit_decision(
        self,
        proposal_id: str,
        device_id: str,
        decision: str,
        note: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Applies an approve/reject decision with replay + expiry protection."""
        self.expire_stale_proposals()

        if decision not in ("approved", "rejected"):
            return False, "Invalid decision string.", None

        proposal = self._get_raw(proposal_id)
        if not proposal:
            return False, "Unknown or malformed proposal ID.", None

        if proposal["status"] not in ("PENDING_REVIEW", "AWAITING_APPROVAL"):
            return False, f"Proposal is already resolved ({proposal['status']}).", None

        if proposal["expires_at"]:
            expires = datetime.datetime.fromisoformat(proposal["expires_at"].rstrip("Z"))
            if datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) > expires:
                self._set_status(proposal_id, "EXPIRED", actor="system", note="Expired before decision.")
                return False, "Proposal expired before a decision was received.", None

        new_status = "APPROVED" if decision == "approved" else "REJECTED"
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE cognitive_proposals
            SET status = ?, resolved_at = ?, resolved_by = ?, resolution_note = ?
            WHERE proposal_id = ?
            """,
            (new_status, now, device_id, note, proposal_id)
        )
        cursor.execute(
            """
            INSERT INTO proposal_event_log
                (event_id, proposal_id, event_type, actor, detail, payload_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"pev_{uuid.uuid4().hex[:12]}",
                proposal_id,
                f"PROPOSAL_{decision.upper()}",
                device_id,
                note,
                self._payload_hash(proposal),
                now,
            )
        )
        conn.commit()
        conn.close()

        logger.info("Proposal %s resolved as %s by device %s", proposal_id, new_status, device_id)
        return True, new_status, self.get_proposal(proposal_id)

    def cancel_proposal(self, proposal_id: str, reason: Optional[str] = None) -> Tuple[bool, str]:
        """Cancels a pending proposal (cognitive loop, emergency stop, or user request)."""
        proposal = self._get_raw(proposal_id)
        if not proposal:
            return False, "Unknown or malformed proposal ID."

        if proposal["status"] not in ("PENDING_REVIEW", "AWAITING_APPROVAL"):
            return False, f"Proposal is already resolved ({proposal['status']})."

        self._set_status(proposal_id, "CANCELLED", actor="system", note=reason or "Cancelled.")
        return True, "CANCELLED"

    def expire_stale_proposals(self) -> int:
        """Marks overdue pending proposals as EXPIRED. Returns count expired."""
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE cognitive_proposals SET status = 'EXPIRED'
            WHERE status IN ('PENDING_REVIEW', 'AWAITING_APPROVAL')
              AND expires_at IS NOT NULL AND expires_at < ?
            """,
            (now,)
        )
        changed = cursor.rowcount
        conn.commit()
        conn.close()
        return changed

    # ==============================================================================
    # EXECUTION RESULTS
    # ==============================================================================

    def record_execution(self, proposal_id: str, success: bool, result: str) -> Tuple[bool, str]:
        """Persists the execution outcome of an approved proposal."""
        proposal = self._get_raw(proposal_id)
        if not proposal:
            return False, "Unknown or malformed proposal ID."

        if proposal["status"] != "APPROVED":
            return False, f"Proposal is not in APPROVED state ({proposal['status']})."

        new_status = "APPLIED" if success else "APPLY_FAILED"
        self._set_status(proposal_id, new_status, actor="executor", note=result)
        return True, new_status

    # ==============================================================================
    # INTERNALS
    # ==============================================================================

    def _get_raw(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the raw DB row as a plain dict (internal use)."""
        if not proposal_id or not isinstance(proposal_id, str) or not proposal_id.startswith("prop_"):
            return None

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cognitive_proposals WHERE proposal_id = ?", (proposal_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def _set_status(self, proposal_id: str, status: str, actor: str, note: Optional[str]):
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        conn = self.get_connection()
        cursor = conn.cursor()

        if status in ("APPROVED", "REJECTED", "CANCELLED", "EXPIRED", "APPLIED", "APPLY_FAILED"):
            cursor.execute(
                """
                UPDATE cognitive_proposals
                SET status = ?, resolved_at = COALESCE(resolved_at, ?), resolution_note = ?
                WHERE proposal_id = ?
                """,
                (status, now, note, proposal_id)
            )
        else:
            cursor.execute(
                "UPDATE cognitive_proposals SET status = ?, resolution_note = ? WHERE proposal_id = ?",
                (status, note, proposal_id)
            )

        cursor.execute(
            """
            INSERT INTO proposal_event_log (event_id, proposal_id, event_type, actor, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"pev_{uuid.uuid4().hex[:12]}", proposal_id, f"STATUS_{status}", actor, note, now)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _payload_hash(proposal: Dict[str, Any]) -> Optional[str]:
        """Hashes the payload of a decision event to create a tamper-evident audit trail."""
        if not proposal or not proposal.get("payload"):
            return None
        import hashlib
        serialized = json.dumps(proposal["payload"], sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# Global active instance
proposal_manager = ProposalManager()