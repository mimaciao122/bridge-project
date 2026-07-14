from pathlib import Path

from bridge.adapters.external_ai_stub import StubExternalAdapter
from bridge.audit.logger import AuditLogger
from bridge.core.contract import BridgeRequest, OperationType, PolicyDecision
from bridge.core.orchestrator import Bridge
from bridge.policy.engine import PolicyEngine


def _bridge(tmp_path: Path, external_provider_enabled: bool = True) -> Bridge:
    return Bridge(
        policy_engine=PolicyEngine(),
        adapter=StubExternalAdapter(),
        audit_logger=AuditLogger(tmp_path / "audit.jsonl"),
        external_provider_enabled=external_provider_enabled,
    )


def test_allowed_operation_uses_adapter_and_logs_audit(tmp_path: Path):
    bridge = _bridge(tmp_path)
    request = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="testo semplice",
        source_id="agente-1",
    )

    response = bridge.handle(request)

    assert response.decision == PolicyDecision.ALLOW
    assert response.provider_used == "external_stub"
    assert response.output is not None

    entries = AuditLogger(tmp_path / "audit.jsonl").read_all()
    assert len(entries) == 1
    assert entries[0]["record"]["decision"] == "allow"


def test_denied_operation_is_still_audited(tmp_path: Path):
    bridge = _bridge(tmp_path)
    request = BridgeRequest(
        operation=OperationType.EXTRACT,
        payload="qualsiasi cosa",
        source_id="agente-1",
    )

    response = bridge.handle(request)

    assert response.decision == PolicyDecision.DENY
    assert response.output is None

    entries = AuditLogger(tmp_path / "audit.jsonl").read_all()
    assert len(entries) == 1
    assert entries[0]["record"]["decision"] == "deny"


def test_external_provider_disabled_flag_blocks_even_allowed_operations(tmp_path: Path):
    bridge = _bridge(tmp_path, external_provider_enabled=False)
    request = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="testo semplice",
        source_id="agente-1",
    )

    response = bridge.handle(request)

    assert response.decision == PolicyDecision.DENY
    assert response.provider_used == "external_disabled"
    assert response.output is None


def test_audit_log_never_contains_raw_payload(tmp_path: Path):
    bridge = _bridge(tmp_path)
    secret_text = "email segreta: mario.rossi@example.com"
    request = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload=secret_text,
        source_id="agente-1",
    )

    bridge.handle(request)

    raw_log = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert secret_text not in raw_log
    assert "mario.rossi" not in raw_log
