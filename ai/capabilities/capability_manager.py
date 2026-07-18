class CapabilityManager:

    def __init__(self):

        self.capabilities = []

    def register(self, capability):

        self.capabilities.append(capability)

    def get_capability(self, task):

        for capability in self.capabilities:

            if capability.can_handle(task):

                return capability

        return None

    def list_capabilities(self):

        return [c.name for c in self.capabilities]