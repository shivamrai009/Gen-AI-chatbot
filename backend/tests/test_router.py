from app.services.router import RouterService


def test_router_rejects_off_topic_query() -> None:
    router = RouterService()
    decision = router.decide("Write me a python script for sorting")
    assert decision.route == "reject"


def test_router_uses_hybrid_for_relational_query() -> None:
    router = RouterService()
    decision = router.decide("How does deployment strategy connect to marketing goals?")
    assert decision.route == "hybrid"


def test_router_clarify_for_short_query() -> None:
    router = RouterService()
    decision = router.decide("roadmap?")
    assert decision.route == "clarify"
