class ConsensusEngine:

    def combine(self, responses):

        if not responses:
            return ""

        # A single answer passes through verbatim — no artificial separator.
        if len(responses) == 1:
            return responses[0]

        final_answer = ""

        for index, response in enumerate(responses):

            final_answer += response

            if index < len(responses) - 1:
                final_answer += "\n\n------------------------\n\n"

        return final_answer