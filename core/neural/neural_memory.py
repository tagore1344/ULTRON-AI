# core/neural/neural_memory.py
import os
import json
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Tuple, Optional

from core.neural.neural_schema import NeuralNodeModel, NeuralEdgeModel

logger = logging.getLogger("ultron-api")

DB_DIR = "backend/data"
DB_PATH = os.path.join(DB_DIR, "ultron_context.db")


class NeuralMemory:
    """Manages SQLite-based persistence, retrieval, and sub-graph queries of the symbolic Neural Schema."""

    def __init__(self):
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Returns thread-safe connection to the context database."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self):
        """Creates neural_nodes and neural_edges schema tables if not present."""
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Table: neural_nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                properties TEXT NOT NULL, -- Serialized JSON
                belief_confidence REAL NOT NULL,
                operational_state TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)

        # 2. Table: neural_edges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS neural_edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES neural_nodes(node_id) ON DELETE CASCADE,
                target_id TEXT NOT NULL REFERENCES neural_nodes(node_id) ON DELETE CASCADE,
                relationship_type TEXT NOT NULL,
                link_confidence REAL NOT NULL,
                causal_influence_delta REAL DEFAULT 0.0,
                UNIQUE(source_id, target_id, relationship_type)
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Neural Schema tables successfully synchronized.")

    def save_node(self, node: NeuralNodeModel) -> bool:
        """Saves or updates a Neural Node record in SQLite."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO neural_nodes (
                    node_id, node_type, label, properties, belief_confidence, operational_state, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    node_type = EXCLUDED.node_type,
                    label = EXCLUDED.label,
                    properties = EXCLUDED.properties,
                    belief_confidence = EXCLUDED.belief_confidence,
                    operational_state = EXCLUDED.operational_state,
                    last_updated = EXCLUDED.last_updated
                """,
                (
                    node.node_id, node.node_type, node.label, json.dumps(node.properties),
                    node.belief_confidence, node.operational_state, node.last_updated
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save neural node '%s': %s", node.node_id, e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def get_node(self, node_id: str) -> Optional[NeuralNodeModel]:
        """Retrieves a single Neural Node by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM neural_nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            r = dict(row)
            return NeuralNodeModel(
                node_id=r["node_id"],
                node_type=r["node_type"],
                label=r["label"],
                properties=json.loads(r["properties"]),
                belief_confidence=r["belief_confidence"],
                operational_state=r["operational_state"],
                last_updated=r["last_updated"]
            )
        return None

    def save_edge(self, edge: NeuralEdgeModel) -> bool:
        """Saves or updates a Neural Edge connection in SQLite."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO neural_edges (
                    edge_id, source_id, target_id, relationship_type, link_confidence, causal_influence_delta
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relationship_type) DO UPDATE SET
                    edge_id = EXCLUDED.edge_id,
                    link_confidence = EXCLUDED.link_confidence,
                    causal_influence_delta = EXCLUDED.causal_influence_delta
                """,
                (
                    edge.edge_id, edge.source_id, edge.target_id, edge.relationship_type,
                    edge.link_confidence, edge.causal_influence_delta
                )
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save neural edge '%s': %s", edge.edge_id, e)
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()

    def get_edge(self, edge_id: str) -> Optional[NeuralEdgeModel]:
        """Retrieves a single Neural Edge by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM neural_edges WHERE edge_id = ?", (edge_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            r = dict(row)
            return NeuralEdgeModel(
                edge_id=r["edge_id"],
                source_id=r["source_id"],
                target_id=r["target_id"],
                relationship_type=r["relationship_type"],
                link_confidence=r["link_confidence"],
                causal_influence_delta=r["causal_influence_delta"]
            )
        return None

    def get_subgraph(self, center_node_id: str, max_depth: int = 2) -> Tuple[List[NeuralNodeModel], List[NeuralEdgeModel]]:
        """
        Retrieves a local sub-graph surrounding the center node ID up to max_depth.
        Prevents prompt context flooding by selecting localized context.
        """
        visited_node_ids = {center_node_id}
        queue = [(center_node_id, 0)]
        edges_list: List[NeuralEdgeModel] = []

        conn = self.get_connection()
        cursor = conn.cursor()

        while queue:
            curr_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            # Fetch outbound and inbound edges
            cursor.execute(
                "SELECT * FROM neural_edges WHERE source_id = ? OR target_id = ?",
                (curr_id, curr_id)
            )
            for row in cursor.fetchall():
                e = dict(row)
                edge_model = NeuralEdgeModel(
                    edge_id=e["edge_id"],
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    relationship_type=e["relationship_type"],
                    link_confidence=e["link_confidence"],
                    causal_influence_delta=e["causal_influence_delta"]
                )
                if edge_model not in edges_list:
                    edges_list.append(edge_model)

                # Track neighbor
                neighbor = e["target_id"] if e["source_id"] == curr_id else e["source_id"]
                if neighbor not in visited_node_ids:
                    visited_node_ids.add(neighbor)
                    queue.append((neighbor, depth + 1))

        # Retrieve all visited node objects
        nodes_list: List[NeuralNodeModel] = []
        for nid in visited_node_ids:
            cursor.execute("SELECT * FROM neural_nodes WHERE node_id = ?", (nid,))
            nrow = cursor.fetchone()
            if nrow:
                r = dict(nrow)
                node_model = NeuralNodeModel(
                    node_id=r["node_id"],
                    node_type=r["node_type"],
                    label=r["label"],
                    properties=json.loads(r["properties"]),
                    belief_confidence=r["belief_confidence"],
                    operational_state=r["operational_state"],
                    last_updated=r["last_updated"]
                )
                nodes_list.append(node_model)

        conn.close()
        return nodes_list, edges_list


# Singleton persistence instance
neural_memory = NeuralMemory()
