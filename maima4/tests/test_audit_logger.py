from pathlib import Path
from uuid import uuid4

from bridge.audit.logger import AuditLogger
from bridge.core.contract import AuditRecord, OperationType, PolicyDecision


def test_audit_logger_integrity(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    record = AuditRecord(
        request_id=uuid4(),
        source_id="user-1",
        operation=OperationType.SUMMARIZE,
        decision=PolicyDecision.ALLOW,
        payload_digest="abc123",
        payload_length=10,
    )
    logger.append(record)

    ok, reason = logger.verify_integrity()
    assert ok
    assert reason is None


def test_audit_logger_detects_tampering(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    record = AuditRecord(
        request_id=uuid4(),
        source_id="user-1",
        operation=OperationType.SUMMARIZE,
        decision=PolicyDecision.ALLOW,
        payload_digest="abc123",
        payload_length=10,
    )
    logger.append(record)

    text = log_path.read_text(encoding="utf-8")
    altered = text.replace("allow", "deny")
    log_path.write_text(altered, encoding="utf-8")

    ok, reason = logger.verify_integrity()
    assert not ok
    assert reason is not None
