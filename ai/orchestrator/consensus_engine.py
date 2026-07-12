class ConsensusEngine:

    def combine(self, responses):

        final_answer = ""

        for response in responses:

            final_answer += response

            final_answer += "\n\n------------------------\n\n"

        return final_answer