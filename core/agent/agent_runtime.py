# core/agent/agent_runtime.py
import asyncio
import datetime
import uuid
import logging
from typing import Dict, Any, Tuple, Optional

from core.agent.task_graph import TaskGraph, TaskNode, NodeState
from core.agent.goal_manager import goal_manager, Goal
from core.agent.planner import planner
from core.update.update_policy import update_policy
from core.agent.policy_engine import policy_engine
from core.agent.tool_orchestrator import tool_orchestrator
from core.agent.critic import critic
from core.agent.recovery_engine import recovery_engine
from core.agent.judgment_engine import judgment_engine, Opinion

# Phase 9B Context and Memory Integrations
from core.context.memory_manager import memory_manager
from core.context.self_model import self_model
from core.context.world_model import world_model
from core.context.long_term_goals import goal_manager_9b

logger = logging.getLogger("ultron-api")


class AgentRuntime:
    """The master coordinator executing the non-blocking asynchronous Cognitive Loop of Matrix Core v2."""

    def __init__(self):
        self.state = "IDLE"  # IDLE, RUNNING, THINKING, FAILING, SUCCESS
        self.active_goal_id: Optional[str] = None
        self.latest_opinion: Optional[Opinion] = None
        self.latest_self_evaluation: Optional[Dict[str, Any]] = None

    def get_status(self) -> Dict[str, Any]:
        """Returns the current real-time state of the autonomous agent pipeline."""
        active_goal = goal_manager.active_goal

        goal_desc = active_goal.description if active_goal else "N/A"
        goal_priority = active_goal.priority if active_goal else "N/A"

        # Update self-model active goal tracking
        self_model.set_autonomy(int(policy_engine.autonomy_level))

        return {
            "state": self.state,
            "goal_id": self.active_goal_id or "N/A",
            "current_goal": goal_desc,
            "priority": goal_priority,
            "autonomy_level": int(policy_engine.autonomy_level),
            "tool_calls_spent": policy_engine.tool_calls_count,
            "tokens_spent": policy_engine.tokens_spent
        }

    def get_opinion(self) -> Optional[Opinion]:
        """Exposes the latest formulated independent opinion."""
        return self.latest_opinion

    def get_self_evaluation(self) -> Optional[Dict[str, Any]]:
        """Exposes the latest self-evaluation metrics and lessons learned."""
        return self.latest_self_evaluation

    async def execute_goal(self, goal_description: str, priority: str = "MEDIUM") -> Tuple[bool, str]:
        """Main non-blocking entrypoint executing the ASI-like 10-step Cognitive Loop with Phase 9B Context."""
        start_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.state = "THINKING"
        policy_engine.reset_counters()

        # 1. INPUT & CONTEXT GATHERING
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        self.active_goal_id = goal_id
        logger.info("Cognitive loop initiated for goal '%s' [%s]", goal_description, goal_id)

        # Update Self Model state tracking
        self_model.active_goals_count += 1
        self_model.set_autonomy(int(policy_engine.autonomy_level))

        # Register goal in Long Term Goals ledger if not already present
        goal_manager_9b.create_goal(
            goal_id=goal_id,
            description=goal_description,
            priority=priority,
            success_criteria="Goal completed successfully without terminal node failures"
        )
        goal_manager_9b.update_goal_status(goal_id, "ACTIVE")

        # 2. CONTEXTUALIZE: Query Persistent Memories via FTS/Recency/Frequency formulas
        logger.info("Phase 9B: Querying persistent memory partitions for context...")
        relevant_memories = memory_manager.get_relevant_memories(goal_description, limit=3)
        for mem in relevant_memories:
            logger.info("Retrieved relevant memory context [%s]: %s", mem.get("source_partition"), mem.get("content") or mem.get("user_prompt"))

        # Update transient Working Memory with goal parameters
        memory_manager.update_working_memory("active_goal_id", goal_id)
        memory_manager.update_working_memory("goal_priority", priority)

        # 3. JUDGMENT FORMULATION
        opinion = judgment_engine.generate_opinion(goal_description)
        self.latest_opinion = opinion

        # Interactive Disagreement Protocol Check
        if opinion.is_disagreement:
            self.state = "IDLE"
            self_model.active_goals_count = max(0, self_model.active_goals_count - 1)
            goal_manager_9b.update_goal_status(goal_id, "CANCELLED")
            logger.warning("Disagreement Protocol triggered! Suboptimal strategy detected in goal.")
            disagreement_msg = (
                f"DISAGREEMENT: {opinion.conclusion}\n"
                f"Justification: {opinion.disagreement_justification}\n"
                f"Recommended Action: {opinion.recommended_action}"
            )
            # Store immediate self-evaluation for self-monitoring
            self.latest_self_evaluation = {
                "goal": goal_description,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "success": False,
                "elapsed_seconds": 0.0,
                "tool_calls_spent": 0,
                "tokens_spent": 0,
                "did_waste_resources": False,
                "what_went_wrong": "Disagreement Protocol triggered: Goal deemed unsafe or suboptimal.",
                "lessons_learned": f"Blocked execution to prevent issues. Recommended: '{opinion.recommended_action}'"
            }

            # Persist the aborted transaction in Episodic Memory
            memory_manager.add_episodic_memory(
                user_prompt=goal_description,
                parsed_intent="disagreement_aborted",
                actual_results=disagreement_msg,
                success_status=False,
                confidence_score=opinion.confidence_score,
                resource_tokens_spent=0,
                resource_latency_sec=0.0,
                goal_id=goal_id
            )

            return False, disagreement_msg

        # 4. GOAL REGISTERING
        active_goal = goal_manager.set_goal(goal_id, goal_description, priority)

        # 5. PLAN GENERATION (Evaluate candidate plans and select best)
        graph = planner.generate_plan(goal_description)
        active_goal.graph = graph
        self.state = "RUNNING"

        success_state = False
        error_summary = None

        try:
            # 6. EXECUTE LOOP (Iterate over ready DAG nodes)
            while not graph.is_complete():
                if active_goal.is_cancelled:
                    logger.warning("Goal execution aborted by user cancellation: %s", goal_id)
                    graph.cancel_all()
                    error_summary = "Execution cancelled by user."
                    break

                ready_nodes = graph.get_ready_nodes()
                if not ready_nodes:
                    logger.error("DAG execution stalled due to blocked dependency nodes.")
                    error_summary = "DAG stalled/deadlocked."
                    break

                for node in ready_nodes:
                    node.state = NodeState.RUNNING
                    logger.info("Executing node: %s - %s", node.id, node.label)

                    # Create subgoal checkpoints statefully inside the ledger
                    # Ensure globally unique subgoal_id across test runs using goal_id prefix
                    subgoal_uid = f"{goal_id}_{node.id}"
                    goal_manager_9b.create_subgoal(
                        subgoal_id=subgoal_uid,
                        goal_id=goal_id,
                        description=node.label,
                        dependencies=",".join(node.dependencies)
                    )
                    goal_manager_9b.update_subgoal_status(subgoal_uid, "RUNNING")

                    # Determine risk level of the intent
                    risk_class = "SAFE"
                    if node.intent in ("system.volume_up", "system.volume_down", "app.open", "system.screenshot"):
                        risk_class = "CONFIRMATION_REQUIRED"
                    elif node.intent in ("shutdown", "restart"):
                        risk_class = "HIGH_RISK"

                    # 7. POLICY CHECK
                    allowed = policy_engine.validate_action(node.intent, risk_class)
                    if not allowed:
                        node.state = NodeState.CANCELLED
                        logger.warning("Policy engine blocked execution of node %s (%s)", node.id, node.label)
                        graph.propagate_failure(node.id)
                        goal_manager_9b.update_subgoal_status(subgoal_uid, "FAILED")
                        error_summary = f"Policy engine blocked intent: {node.intent}"
                        continue

                    policy_engine.increment_tool_call()
                    policy_engine.spend_tokens(500)

                    # 8. SECURE TOOL EXECUTION (Strict ToolRegistry integration)
                    result = await tool_orchestrator.execute_action(node.intent, node.target)
                    logger.info("Node %s result: '%s'", node.id, result)

                    # 9. CRITIQUE & RECOVERY VERIFICATION
                    success = critic.evaluate_result(result)
                    if success:
                        node.state = NodeState.SUCCESS
                        goal_manager_9b.update_subgoal_status(subgoal_uid, "SUCCESS")
                    else:
                        recovery_decision = recovery_engine.handle_failure(node)
                        if recovery_decision == "FAIL":
                            graph.propagate_failure(node.id)
                            goal_manager_9b.update_subgoal_status(subgoal_uid, "FAILED")
                            error_summary = f"Execution failed at node {node.id}."
                        else:
                            # Log retry tracking
                            goal_manager_9b.update_subgoal_status(subgoal_uid, "PENDING")

                await asyncio.sleep(0.01)

            # Determine final success status
            if active_goal.is_cancelled:
                success_state = False
                goal_manager_9b.update_goal_status(goal_id, "CANCELLED")
            elif graph.has_failures():
                success_state = False
                goal_manager_9b.update_goal_status(goal_id, "FAILED")
            else:
                success_state = True
                goal_manager_9b.update_goal_status(goal_id, "COMPLETED")

        except Exception as e:
            logger.error("Cognitive loop transaction exception: %s", e, exc_info=True)
            error_summary = f"Loop execution crashed: {str(e)}"
            success_state = False
            goal_manager_9b.update_goal_status(goal_id, "FAILED")
        finally:
            self.state = "IDLE"
            goal_manager.clear_goal()
            self.active_goal_id = None

            # Reset Self Model tracking
            self_model.active_goals_count = max(0, self_model.active_goals_count - 1)

            # 10. SELF-EVALUATION & REFLECTION
            end_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            elapsed_seconds = (end_time - start_time).total_seconds()

            # Record continuous evaluation metrics statefully
            lessons = "Plan executed perfectly with nominal resource expenditure." if success_state else f"Plan execution failed: {error_summary or 'Incomplete graph'}"
            self.latest_self_evaluation = {
                "goal": goal_description,
                "timestamp": end_time.isoformat() + "Z",
                "success": success_state,
                "elapsed_seconds": elapsed_seconds,
                "tool_calls_spent": policy_engine.tool_calls_count,
                "tokens_spent": policy_engine.tokens_spent,
                "did_waste_resources": policy_engine.tool_calls_count > 5,
                "what_went_wrong": error_summary,
                "lessons_learned": lessons
            }

            logger.info("Continuous self-evaluation stored: %s", self.latest_self_evaluation)

            # Phase 9B Memory Updates
            # A. Log result to Episodic Memory
            memory_manager.add_episodic_memory(
                user_prompt=goal_description,
                parsed_intent="composite" if graph.is_complete() else "chat",
                actual_results=lessons,
                success_status=success_state,
                confidence_score=opinion.confidence_score,
                resource_tokens_spent=policy_engine.tokens_spent,
                resource_latency_sec=elapsed_seconds,
                goal_id=goal_id
            )

            # B. Log to Strategy / Procedural Memory if successful
            if success_state:
                serialized_dag = str(list(graph.nodes.keys()))
                memory_manager.add_strategy_memory(
                    task_pattern=goal_description,
                    successful_dag_structure=serialized_dag,
                    failed_attempts_count=0,
                    successful_runs_count=1,
                    average_latency=elapsed_seconds
                )
            else:
                # C. Log failure parameters in Failure memory & Self Model locks
                memory_manager.add_failure_memory(
                    task_pattern=goal_description,
                    failed_node_intent=error_summary or "unspecified",
                    error_signature=error_summary or "DAG node failed permanently",
                    recovery_decision_applied="FAIL",
                    context_snapshot=str(self_model.get_summary())
                )
                self_model.register_failure(error_summary or "unspecified")

            # Clear transient Working Memory of active session bounds
            memory_manager.clear_working_memory()

        if success_state:
            return True, "Autonomous goal completed successfully."
        else:
            return False, f"Autonomous execution finished with failure. Detail: {error_summary or 'DAG failures detected'}"


# Global active instance of the Matrix Core runtime
agent_runtime = AgentRuntime()
