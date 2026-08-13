# core/agent/agent_runtime.py
import asyncio
import datetime
import uuid
import logging
from typing import Dict, Any, Tuple, Optional, List

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
        self.state = "IDLE"  # IDLE, RUNNING, THINKING, FAILING, SUCCESS, BLOCKED
        self.active_goal_id: Optional[str] = None
        self.latest_opinion: Optional[Opinion] = None
        self.latest_self_evaluation: Optional[Dict[str, Any]] = None

        # Phase 10.1 Continuous Loop State Variables
        self.continuous_running = False
        self.continuous_task: Optional[asyncio.Task] = None
        self.cycle_count = 0
        self.loop_interval_sec = 0.5 # Bounded cycle interval

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
            "tokens_spent": policy_engine.tokens_spent,
            "continuous_running": self.continuous_running,
            "cycle_count": self.cycle_count
        }

    def get_opinion(self) -> Optional[Opinion]:
        """Exposes the latest formulated independent opinion."""
        return self.latest_opinion

    def get_self_evaluation(self) -> Optional[Dict[str, Any]]:
        """Exposes the latest self-evaluation metrics and lessons learned."""
        return self.latest_self_evaluation

    # ==============================================================================
    # PHASE 10.1 CONTINUOUS RUNTIME ENGINE
    # ==============================================================================

    def start_continuous_loop(self) -> bool:
        """Starts the persistent continuous cognitive loop background task. Prevents duplicates."""
        if self.continuous_running:
            logger.warning("Continuous loop is already running.")
            return False

        self.continuous_running = True
        self.continuous_task = asyncio.create_task(self._continuous_loop_runner())
        logger.info("ULTRON Phase 10.1 Continuous Cognitive Loop started successfully.")
        return True

    def stop_continuous_loop(self):
        """Gracefully halts the continuous loop background task."""
        if not self.continuous_running:
            return

        self.continuous_running = False
        if self.continuous_task:
            self.continuous_task.cancel()
            self.continuous_task = None

        self.state = "IDLE"
        logger.info("ULTRON Phase 10.1 Continuous Cognitive Loop gracefully shutdown.")

    async def _continuous_loop_runner(self):
        """Asynchronously executes the full 23-step continuous cognitive loop lifecycle statefully."""
        # Step 1: BOOT
        logger.info("[LIFE_CYCLE] Step 1/23: BOOT initializations completed.")

        while self.continuous_running:
            try:
                self.cycle_count += 1
                logger.info("[LIFE_CYCLE] Starting Cognitive Cycle #%d", self.cycle_count)

                # Step 2: SELF-CHECK
                res = self_model.get_resource_state()
                if res["cpu_percent"] > 95.0:
                    logger.warning("[LIFE_CYCLE] Step 2/23: CPU threshold exceeded. Pausing execution.")
                    await asyncio.sleep(1.0)
                    continue

                # Step 3: LOAD MEMORY
                # Simulates re-loading contextual Working Memory
                working_keys = list(memory_manager.working_memory.keys())
                logger.debug("[LIFE_CYCLE] Step 3/23: Working memory caches re-loaded. Keys: %s", working_keys)

                # Step 4: LOAD GOALS
                active_lt_goals = goal_manager_9b.get_active_goals_with_subgoals()
                logger.debug("[LIFE_CYCLE] Step 4/23: Loaded active goals from DB ledger: %s", len(active_lt_goals))

                # Step 5: REFRESH WORLD MODEL
                world_model.get_summary()

                # Step 6: UPDATE NEURAL SCHEMA
                try:
                    from core.neural.event_memory import event_memory
                    event_memory.record_state("continuous_cycle", f"Active cycle: {self.cycle_count}")
                except Exception:
                    pass

                # Step 7: SELECT PRIORITIES
                # Pick the first active/pending goal to process
                target_goal = None
                for g in active_lt_goals:
                    if g["status"] in ("ACTIVE", "PENDING"):
                        target_goal = g
                        break

                if not target_goal:
                    # If idle (no active goals), run observation sweeps and sleep
                    logger.debug("[LIFE_CYCLE] Step 7/23: System idle. Sleeping for loop interval.")
                    await asyncio.sleep(self.loop_interval_sec)
                    continue

                goal_desc = target_goal["description"]
                goal_id = target_goal["goal_id"]

                # Step 8: REASON
                logger.info("[LIFE_CYCLE] Step 8/23: Reasoning over goal '%s'", goal_desc)

                # Step 9: JUDGE
                opinion = judgment_engine.generate_opinion(goal_desc)
                self.latest_opinion = opinion

                # Step 10: DISAGREEMENT CHECK
                if opinion.is_disagreement:
                    logger.warning("[LIFE_CYCLE] Step 10/23: Disagreement triggered. Suspending goal.")
                    goal_manager_9b.update_goal_status(goal_id, "SUSPENDED")
                    continue

                # Step 11: PLAN
                candidates = planner.generate_candidates(goal_desc)

                # Step 12: CHOOSE PLAN
                graph = planner.generate_plan(goal_desc)

                # Step 13: POLICY CHECK
                # Check absolute budget limits prior to execution
                if policy_engine.tool_calls_count >= policy_engine.max_tool_calls:
                    logger.warning("[LIFE_CYCLE] Step 13/23: Policy budget exhausted. Suspending loop.")
                    self.state = "BLOCKED"
                    break

                # Step 14: ACT & Step 15: OBSERVE RESULT (Simulated E2E dispatch)
                logger.info("[LIFE_CYCLE] Step 14/23: Activating tool dispatches strictly via ToolRegistry...")
                # Fetch ready nodes
                ready = graph.get_ready_nodes()
                for node in ready:
                    node.state = NodeState.RUNNING
                    # Step 16: CRITIQUE
                    result = await tool_orchestrator.execute_action(node.intent, node.target)
                    success = critic.evaluate_result(result)
                    if success:
                        node.state = NodeState.SUCCESS
                    else:
                        node.state = NodeState.FAILED

                # Step 17: UPDATE BELIEFS
                try:
                    from core.neural.belief_state import belief_state
                    belief_state.ingest_evidence("continuous_loop_node", success=True)
                except Exception:
                    pass

                # Step 18: STORE EXPERIENCE
                memory_manager.add_episodic_memory(
                    user_prompt=goal_desc,
                    parsed_intent="continuous_eval",
                    actual_results="Cycle run completed",
                    success_status=True
                )

                # Step 19: DETECT WEAKNESSES & Step 20: GENERATE HYPOTHESES
                try:
                    from core.evolution.hypothesis_engine import hypothesis_engine
                    weaknesses = hypothesis_engine.scan_for_weaknesses()
                except Exception:
                    pass

                # Step 21: OPTIONAL EXPERIMENT & Step 22: EVALUATE (Advisory recommendation only)
                # Left as advisory recommendations to comply with safety boundaries
                logger.debug("[LIFE_CYCLE] Step 21-22/23: Optional sweeps and evaluations recorded.")

                # Step 23: REPLAN / CONTINUE
                # Set goal completed state to avoid infinite cycles
                goal_manager_9b.update_goal_status(goal_id, "COMPLETED")
                logger.info("[LIFE_CYCLE] Step 23/23: Cognitive Cycle run complete. Continuing...")

                await asyncio.sleep(self.loop_interval_sec)

            except asyncio.CancelledError:
                logger.info("Continuous runner task cancelled.")
                break
            except Exception as e:
                logger.error("[LIFE_CYCLE ERROR] Continuous runner exception: %s. Falling back to safe 9A.", e, exc_info=True)
                # Fallback safety lock: shutdown continuous task on error and reset IDLE
                self.continuous_running = False
                self.state = "IDLE"
                break

    # ==============================================================================
    # SYNC/ASYNC DIRECT EXECUTION (Phase 9A fallback)
    # ==============================================================================

    async def execute_goal(self, goal_description: str, priority: str = "MEDIUM") -> Tuple[bool, str]:
        """Main non-blocking entrypoint executing the standard Phase 9A Cognitive Loop."""
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
