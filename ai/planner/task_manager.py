from .task import Task


class TaskManager:

    def __init__(self):

        self.tasks = []

    def add_task(self, task: Task):

        self.tasks.append(task)

        self.tasks.sort(
            key=lambda x: x.priority
        )

    def get_next_task(self):

        for task in self.tasks:

            if task.status == "pending":

                return task

        return None

    def complete_task(self, task: Task):

        task.complete()

    def remove_completed(self):

        self.tasks = [

            task

            for task in self.tasks

            if task.status != "completed"

        ]

    def show_tasks(self):

        for task in self.tasks:

            print(task)