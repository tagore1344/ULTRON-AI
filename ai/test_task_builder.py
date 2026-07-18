from ai.planner.llm_planner import LLMPlanner
from ai.planner.task_builder import TaskBuilder

planner = LLMPlanner()
builder = TaskBuilder()

while True:

    user = input("You: ")

    if user.lower() == "exit":
        break

    plan = planner.create_plan(user)

    tasks = builder.build(plan)

    print("\nGenerated Tasks:\n")

    for task in tasks:
        print(task)