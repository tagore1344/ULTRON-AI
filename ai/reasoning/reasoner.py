class Reasoner:

    def __init__(self, memory):

        self.memory = memory

    def analyze(self, user_request, plan):

        context = {
            "original_request": user_request,
            "plan": plan,
            "memory": self.memory.dump_short_memory()
        }

        return context