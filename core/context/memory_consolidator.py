# core/context/memory_consolidator.py
import json
import sqlite3
import logging
import datetime
from typing import Dict, Any, List

from core.context.memory_manager import memory_manager, sanitize_sensitive_data
from core.context.self_model import self_model
from core.context.world_model import world_model
from core.neural.neural_memory import neural_memory
from core.neural.concept_graph import concept_graph
from core.neural.relation_graph import relation_graph
from core.neural.schema_reasoner import schema_reasoner
from core.neural.belief_state import belief_state

logger = logging.getLogger("ultron-api")


class MemoryConsolidator:
    """Performs background memory consolidation, transforming highly valued experiences into Neural Schema Concepts."""

    def __init__(self):
        self.is_running = False
        self.consolidation_count = 0

    def calculate_importance_score(self, episode: Dict[str, Any]) -> float:
        """
        Calculates an importance score (0.0 to 10.0) based on:
        Success (4.0 max), Rarity/Latency (3.0 max), and Error/Failure Significance (3.0 max).
        """
        score = 0.0

        # 1. Success/Failure significance (Max 4.0)
        success = bool(episode.get("success_status", False))
        if not success:
            score += 3.5  # Failures are highly valuable for debugging and avoidance
        else:
            score += 2.0  # Basic successes

        # 2. Latency delta significance (Max 3.0)
        latency = float(episode.get("resource_latency_sec", 0.0))
        if latency > 1.5:
            score += 3.0  # High latency is a significant bottleneck
        elif latency > 0.5:
            score += 1.5

        # 3. Rarity / Goal relevance (Max 3.0)
        intent = str(episode.get("parsed_intent", "")).lower()
        if "composite" in intent or "disagreement" in intent:
            score += 3.0  # High cognitive complexity is highly relevant
        else:
            score += 1.0

        return min(10.0, score)

    def run_consolidation_sweep(self) -> bool:
        """
        Executes a complete 10.2 memory consolidation run.
        Pulls episodes, calculates importance, filters >= 8.0, and updates the Neural Graph.
        """
        if self.is_running:
            return False

        self.is_running = True
        logger.info("[CONSOLIDATION] Initiating memory consolidation sweep...")
        self.consolidation_count += 1

        # Resource budget guard (CPU/RAM check before starting)
        res = self_model.get_resource_state()
        if res["cpu_percent"] > 90.0:
            logger.warning("[CONSOLIDATION] Throttled: CPU is too high (%s%%). Aborting sweep.", res["cpu_percent"])
            self.is_running = False
            return False

        episodes = []
        try:
            conn = memory_manager.get_connection()
            cursor = conn.cursor()
            # 1. Fetch all unconsolidated episodic memories
            cursor.execute("SELECT * FROM episodic_memory")
            episodes = [dict(row) for row in cursor.fetchall()]
            # Cleanly close connection immediately to release read-locks prior to neural writes
            conn.close()
        except Exception as e:
            logger.error("[CONSOLIDATION ERROR] Failed to fetch episodic memories: %s", e)
            self.is_running = False
            return False

        try:
            # 2. Iterate and process episodes
            for ep in episodes:
                importance = self.calculate_importance_score(ep)

                # Persist the calculated importance score back to episodic table
                write_conn = memory_manager.get_connection()
                try:
                    write_cursor = write_conn.cursor()
                    write_cursor.execute(
                        "UPDATE episodic_memory SET importance_score = ? WHERE memory_id = ?",
                        (importance, ep["memory_id"])
                    )
                    write_conn.commit()
                except Exception as ex:
                    logger.error("Failed to update episodic importance: %s", ex)
                finally:
                    write_conn.close()

                # 3. Filter High-Value Memories (Importance >= 8.0)
                if importance >= 8.0:
                    logger.info("[CONSOLIDATION] High-value memory identified (%s). Processing...", ep["memory_id"])

                    # Extract properties
                    prompt = ep["user_prompt"]
                    results = ep["actual_results"]
                    intent = ep["parsed_intent"]

                    # Privacy Sanitization Check (Reds credentials again before consolidation)
                    sanitized_prompt = sanitize_sensitive_data(prompt)
                    sanitized_results = sanitize_sensitive_data(results)

                    # 4. Contradiction Checking
                    # Compare with existing beliefs before saving
                    node_id = f"concept_{intent}"
                    existing_node = neural_memory.get_node(node_id)
                    if existing_node:
                        # Reconcile any subjective contradiction with observed fact
                        schema_reasoner.verify_and_reconcile(node_id, observed_success=bool(ep["success_status"]))
                    else:
                        # 5. Extract and add Concept Node to Neural Schema Graph
                        concept_graph.add_concept(
                            concept_id=node_id,
                            label=f"Concept for intent: {intent}",
                            properties={
                                "last_prompt": sanitized_prompt,
                                "last_outcome": sanitized_results,
                                "importance_level": importance
                            }
                        )

                        # Establish causal edge to its parent world status
                        relation_graph.add_relation(
                            source_id="self_model_status",
                            target_id=node_id,
                            relationship_type="ASSOCIATED_WITH",
                            link_confidence=0.90
                        )

            # 6. Bounded Confidence Decay for low-frequency knowledge
            self.apply_confidence_decay()
            logger.info("[CONSOLIDATION] Memory consolidation sweep finished successfully.")
            return True

        except Exception as e:
            logger.error("[CONSOLIDATION ERROR] Transaction crash during sweep: %s", e)
            return False
        finally:
            self.is_running = False

    def apply_confidence_decay(self):
        """
        Decays the subjective belief confidence (B) of unverified, low-frequency semantic concepts.
        Does NOT erase highly verified, known factual statements (B >= 0.85).
        """
        logger.debug("[CONSOLIDATION] Applying confidence decay on unverified knowledge...")
        conn = neural_memory.get_connection()
        cursor = conn.cursor()

        try:
            # Query unverified nodes
            cursor.execute("SELECT node_id FROM neural_nodes WHERE operational_state = 'UNVERIFIED'")
            rows = cursor.fetchall()
            for r in rows:
                node_id = r["node_id"]
                node = neural_memory.get_node(node_id)
                if node:
                    # Decay confidence by 5%
                    node.belief_confidence = round(max(0.0, node.belief_confidence * 0.95), 3)
                    node.operational_state = node.evaluate_operational_state()
                    neural_memory.save_node(node)
                    logger.debug("[CONSOLIDATION] Decayed confidence of node '%s' to %.3f", node_id, node.belief_confidence)
        except Exception as e:
            logger.error("[CONSOLIDATION] Failed to apply confidence decay: %s", e)
        finally:
            conn.close()


# Singleton consolidator instance
memory_consolidator = MemoryConsolidator()
