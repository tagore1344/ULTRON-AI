class ModelSelector:

    def choose_model(self, prompt):

        prompt = prompt.lower()

        if "code" in prompt:
            return "gemini"

        elif "python" in prompt:
            return "gemini"

        elif "cyber" in prompt:
            return "gemini"

        else:
            return "gemini"