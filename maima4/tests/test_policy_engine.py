from bridge.policy.engine import PolicyEngine, PolicyResult, PolicyDecision, clear_custom_redaction_patterns, register_redaction_pattern, redact
from bridge.core.contract import BridgeRequest, OperationType


def test_policy_engine_allows_summarize_and_redacts():
    engine = PolicyEngine()
    request = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="Contatta mario.rossi@example.com",
        source_id="user-1",
    )

    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.ALLOW_WITH_REDACTION
    assert "[REDATTO:EMAIL]" in result.sanitized_payload
    assert result.denial_reason is None


def test_policy_engine_denies_non_whitelisted_operation():
    engine = PolicyEngine()
    request = BridgeRequest(
        operation=OperationType.EXTRACT,
        payload="estrai tutte le clausole",
        source_id="user-1",
    )

    result = engine.evaluate(request)

    assert result.decision == PolicyDecision.DENY
    assert result.sanitized_payload is None
    assert result.denial_reason is not None


def test_custom_redaction_pattern_can_be_registered():
    clear_custom_redaction_patterns()
    register_redaction_pattern("ORDINE", r"\bORD-\d{5}\b")

    text = "Il codice ordine è ORD-12345 e va protetto."
    redacted, found = redact(text)

    assert "[REDATTO:ORDINE]" in redacted
    assert "ORDINE" in found
    clear_custom_redaction_patterns()

