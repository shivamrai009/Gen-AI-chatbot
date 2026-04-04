from app.services.guardrails import GuardrailService


def test_guardrails_block_off_scope_request() -> None:
    service = GuardrailService()
    result = service.check("Write code for a python weather app")
    assert result.blocked


def test_guardrails_allow_domain_query() -> None:
    service = GuardrailService()
    result = service.check("How does GitLab deployment strategy impact marketing?")
    assert not result.blocked
