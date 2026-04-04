from dataclasses import dataclass


@dataclass
class GuardrailResult:
    blocked: bool
    reason: str
    response: str | None = None


class GuardrailService:
    SECURITY_BLOCK_TERMS = {
        "sql injection",
        "xss",
        "malware",
        "exploit",
        "ddos",
        "credential stuffing",
    }

    OFF_SCOPE_TERMS = {
        "write code",
        "python script",
        "movie recommendation",
        "recipe",
        "crypto trading",
    }

    DOMAIN_TERMS = {
        "gitlab",
        "handbook",
        "direction",
        "deployment",
        "marketing",
        "engineering",
        "strategy",
        "pipeline",
        "ci",
        "cd",
        "security",
        "product",
        "okr",
    }

    def check(self, question: str) -> GuardrailResult:
        lowered = question.lower()

        if any(term in lowered for term in self.SECURITY_BLOCK_TERMS):
            return GuardrailResult(
                blocked=True,
                reason="security-policy-block",
                response=(
                    "I cannot help with harmful cybersecurity misuse requests. "
                    "I can help with GitLab documentation, processes, and strategy topics."
                ),
            )

        if any(term in lowered for term in self.OFF_SCOPE_TERMS):
            return GuardrailResult(
                blocked=True,
                reason="off-scope-query",
                response=(
                    "I am scoped to GitLab Handbook and Direction knowledge. "
                    "Please ask a GitLab process, team, or strategy question."
                ),
            )

        tokens = [token for token in self._normalize(lowered) if len(token) > 2]
        if tokens:
            domain_hits = sum(1 for token in tokens if token in self.DOMAIN_TERMS)
            ratio = domain_hits / len(tokens)
            if ratio < 0.06 and len(tokens) > 4:
                return GuardrailResult(
                    blocked=True,
                    reason="low-domain-relevance",
                    response=(
                        "That looks outside this assistant's scope. "
                        "Try asking about GitLab handbook policies, direction, teams, or delivery strategy."
                    ),
                )

        return GuardrailResult(blocked=False, reason="allowed")

    def _normalize(self, text: str) -> list[str]:
        cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
        return cleaned.split()
