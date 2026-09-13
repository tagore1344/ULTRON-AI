class ModelSelector:
    """Routes prompts to the best-suited AI provider.

    Strategy (per PROJECT_REVIEW recommendation):
      * coding / math / technical prompts  -> Gemini first (strong technical base)
      * cybersecurity / reasoning prompts  -> DeepSeek first
      * general conversational prompts     -> OpenAI first

    Every ranked position is followed by all remaining providers as automatic
    fallbacks, so the orchestrator always has a route even if a provider's key
    is missing. Selection respects live provider availability.
    """

    # Keyword routing tables (lower-cased substring matching)
    CODE_KEYWORDS = (
        "code", "python", "javascript", "java ", "sql", "regex",
        "algorithm", "function", "debug", "refactor", "compile",
        "math", "calculate", "equation", "solve for", "formula",
        "geometry", "physics problem",
    )
    SECURITY_KEYWORDS = (
        "cyber", "security", "exploit", "vulnerability", "malware",
        "encrypt", "penetration", "firewall", "phishing", "attack",
        "forensic", "threat", "harden", "reason through", "logic puzzle",
    )

    def rank_models(self, prompt, available=None):
        """Returns the full provider preference order for a prompt.

        `available` is an optional dict of {provider_name: bool}. When omitted,
        live availability probes are consulted; providers that are down are
        still listed but pushed to the end instead of being hidden entirely.
        """
        prompt_lower = (prompt or "").lower()

        primary = "gemini"  # safest default: matches historical behavior

        if any(keyword in prompt_lower for keyword in self.CODE_KEYWORDS):
            primary = "gemini"
            secondary = ["deepseek", "openai"]
        elif any(keyword in prompt_lower for keyword in self.SECURITY_KEYWORDS):
            primary = "deepseek"
            secondary = ["gemini", "openai"]
        else:
            primary = "openai"
            secondary = ["gemini", "deepseek"]

        all_providers = [primary] + secondary

        if available is None:
            available = get_provider_availability()

        online = [p for p in all_providers if available.get(p)]
        offline = [p for p in all_providers if not available.get(p)]

        # Available providers keep the strategic order; offline ones trail behind
        # so orchestrator fallbacks can attempt them last if keys appear later.
        return online + offline

    def choose_model(self, prompt):
        """Chooses the single best AVAILABLE provider for this prompt."""
        ranked = self.rank_models(prompt)
        return ranked[0] if ranked else "gemini"


def get_provider_availability():
    """Non-network availability probe for every configured AI provider."""
    availability = {}

    try:
        from ai.agents.gemini_agent import is_gemini_available
        availability["gemini"] = bool(is_gemini_available())
    except Exception:
        availability["gemini"] = False

    try:
        from ai.agents.openai_agent import is_openai_available
        availability["openai"] = bool(is_openai_available())
    except Exception:
        availability["openai"] = False

    try:
        from ai.agents.deepseek_agent import is_deepseek_available
        availability["deepseek"] = bool(is_deepseek_available())
    except Exception:
        availability["deepseek"] = False

    return availability