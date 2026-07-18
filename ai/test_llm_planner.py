from ai.planner.llm_planner import LLMPlanner

planner = LLMPlanner()

while True:

    user = input("You: ")

    if user.lower() == "exit":
        break

    tasks = planner.create_plan(user)

    print("\nGenerated Plan:\n")

    print(tasks)
