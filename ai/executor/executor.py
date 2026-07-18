from .execution_context import ExecutionContext
from .tool_executor import ToolExecutor


class Executor:

    def __init__(self, speech):

        self.context = ExecutionContext()

        self.tool_executor = ToolExecutor(speech)

    def execute_tasks(self, tasks):

        results = []

        for task in tasks:

            self.context.start(task.name)

            try:

                result = self.tool_executor.execute(task)

                self.context.complete()

                results.append(result)

            except Exception as e:

                self.context.fail()

                results.append(str(e))

        return results