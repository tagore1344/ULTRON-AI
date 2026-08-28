class ConsensusEngine:

    def combine(self, responses):

        if not responses:
            return ""

        # A single answer passes through verbatim — no artificial separator.
        if len(responses) == 1:
            return responses[0]

        # Multiple answers are joined with clean blank lines only — no
        # separator artifacts ("-----") and no provider names leak into
        # the final user-facing text.
        return "\n\n".join(str(r) for r in responses)