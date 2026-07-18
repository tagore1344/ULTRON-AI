from ai.planner.planner import Planner

planner = Planner()

while True:

    user = input("You: ")

    if user.lower() == "exit":
        break

    tasks = planner.create_plan(user)

    print("\nGenerated Tasks:\n")

    for task in tasks:
        print(task)