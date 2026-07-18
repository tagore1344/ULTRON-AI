from ai.planner.llm_planner import LLMPlanner
from ai.planner.task_builder import TaskBuilder
from ai.executor.executor import Executor
from ai.memory.memory_manager import MemoryManager
from ai.reasoning.reasoner import Reasoner


class AgentPipeline:

    def __init__(self, speech):

        self.planner = LLMPlanner()

        self.memory = MemoryManager()

        self.reasoner = Reasoner(self.memory)

        self.builder = TaskBuilder()

        self.executor = Executor(speech)

    def run(self, user_request):

        print("\n========== STEP 1 ==========")
        print("Creating Plan...")

        plan = self.planner.create_plan(user_request)

        print(plan)

        print("\n========== STEP 2 ==========")
        print("Reasoning...")

        context = self.reasoner.analyze(user_request, plan)

        print(context)

        print("\n========== STEP 3 ==========")
        print("Building Tasks...")

        tasks = self.builder.build(plan)

        for task in tasks:
            print(task)

        print("\n========== STEP 4 ==========")
        print("Executing Tasks...")

        results = self.executor.execute_tasks(tasks)

        # Save execution in memory
        self.memory.remember("last_command", user_request)
        self.memory.remember("last_plan", plan)
        self.memory.remember("last_tasks", tasks)
        self.memory.remember("last_result", results)

        print("\n========== MEMORY ==========")
        print(self.memory.dump_short_memory())

        return results