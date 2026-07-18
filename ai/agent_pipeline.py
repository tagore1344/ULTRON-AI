from ai.planner.llm_planner import LLMPlanner
from ai.planner.task_builder import TaskBuilder
from ai.executor.executor import Executor


class AgentPipeline:

    def __init__(self, speech):

        # Shared speech engine
        self.speech = speech

        # AI Planner
        self.planner = LLMPlanner()

        # Converts plan into executable tasks
        self.builder = TaskBuilder()

        # Executor uses the same speech engine
        self.executor = Executor(speech)

    def run(self, user_request):

        print("\n========== STEP 1 ==========")
        print("Creating Plan...")

        plan = self.planner.create_plan(user_request)

        print(plan)

        print("\n========== STEP 2 ==========")
        print("Building Tasks...")

        tasks = self.builder.build(plan)

        for task in tasks:
            print(task)

        print("\n========== STEP 3 ==========")
        print("Executing Tasks...")

        results = self.executor.execute_tasks(tasks)

        return results