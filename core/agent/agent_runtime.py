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
        """Main non-blocking entrypoint executing the ASI-like 10-step Cognitive Loop."""
        start_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        self.state = "THINKING"
        policy_engine.reset_counters()

        # 1. INPUT & CONTEXT GATHERING
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        self.active_goal_id = goal_id
        logger.info("Cognitive loop initiated for goal '%s' [%s]", goal_description, goal_id)

        # 2. JUDGMENT FORMULATION
        # Analyze goal independently, question assumptions, construct evidence-based opinion
        opinion = judgment_engine.generate_opinion(goal_description)
        self.latest_opinion = opinion

        # Interactive Disagreement Protocol Check
        if opinion.is_disagreement:
            self.state = "IDLE"
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
            return False, disagreement_msg

        # 3. GOAL REGISTERING
        active_goal = goal_manager.set_goal(goal_id, goal_description, priority)

        # 4. PLAN GENERATION (Evaluate candidate plans and select best)
        graph = planner.generate_plan(goal_description)
        active_goal.graph = graph
        self.state = "RUNNING"

        success_state = False
        error_summary = None

        try:
            # 5. EXECUTE LOOP (Iterate over ready DAG nodes)
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

                    # Determine risk level of the intent
                    risk_class = "SAFE"
                    if node.intent in ("system.volume_up", "system.volume_down", "app.open", "system.screenshot"):
                        risk_class = "CONFIRMATION_REQUIRED"
                    elif node.intent in ("shutdown", "restart"):
                        risk_class = "HIGH_RISK"

                    # 6. POLICY CHECK
                    allowed = policy_engine.validate_action(node.intent, risk_class)
                    if not allowed:
                        node.state = NodeState.CANCELLED
                        logger.warning("Policy engine blocked execution of node %s (%s)", node.id, node.label)
                        graph.propagate_failure(node.id)
                        error_summary = f"Policy engine blocked intent: {node.intent}"
                        continue

                    policy_engine.increment_tool_call()
                    policy_engine.spend_tokens(500)

                    # 7. SECURE TOOL EXECUTION (Strict ToolRegistry integration)
                    result = await tool_orchestrator.execute_action(node.intent, node.target)
                    logger.info("Node %s result: '%s'", node.id, result)

                    # 8. CRITIQUE & RECOVERY VERIFICATION
                    success = critic.evaluate_result(result)
                    if success:
                        node.state = NodeState.SUCCESS
                    else:
                        recovery_decision = recovery_engine.handle_failure(node)
                        if recovery_decision == "FAIL":
                            graph.propagate_failure(node.id)
                            error_summary = f"Execution failed at node {node.id}."

                await asyncio.sleep(0.01)

            # Determine final success status
            if active_goal.is_cancelled:
                success_state = False
                error_summary = "Goal cancelled by user."
            elif graph.has_failures():
                success_state = False
            else:
                success_state = True

        except Exception as e:
            logger.error("Cognitive loop transaction exception: %s", e, exc_info=True)
            error_summary = f"Loop execution crashed: {str(e)}"
            success_state = False
        finally:
            self.state = "IDLE"
            goal_manager.clear_goal()
            self.active_goal_id = None

            # 9. SELF-EVALUATION & REFLECTION
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

        if success_state:
            return True, "Autonomous goal completed successfully."
        else:
            return False, f"Autonomous execution finished with failure. Detail: {error_summary or 'DAG failures detected'}"


# Global active instance of the Matrix Core runtime
agent_runtime = AgentRuntime()
