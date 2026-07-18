class Capability:

    def __init__(self, name, description):

        self.name = name

        self.description = description

    def can_handle(self, task):

        return False

    def execute(self, task):

        raise NotImplementedError