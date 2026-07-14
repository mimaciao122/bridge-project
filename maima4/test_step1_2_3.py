"""
Test manuale end-to-end per Step 1 + Step 2 + Step 3.
Esegui con:  python3 test_step1_2_3.py
(richiede: pip install pydantic)

Il log di audit viene scritto in ./audit_test.jsonl (cancellalo per ripartire
da zero tra un'esecuzione e l'altra, se vuoi una catena di hash pulita).
"""

import json
from pathlib import Path

from bridge.audit.logger import AuditLogger
from bridge.adapters.external_ai_stub import StubExternalAdapter
from bridge.core.contract import BridgeRequest, OperationType
from bridge.core.orchestrator import Bridge
from bridge.policy.engine import PolicyEngine, RateLimiter


LOG_PATH = Path("audit_test.jsonl")


def main() -> None:
    # log pulito ad ogni esecuzione, per un output leggibile
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    bridge = Bridge(
        policy_engine=PolicyEngine(),
        adapter=StubExternalAdapter(),
        audit_logger=AuditLogger(LOG_PATH),
    )

    # Caso 1: operazione permessa + dati sensibili -> allow_with_redaction
    r1 = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="Contatta mario.rossi@example.com per il bonifico di 1.250,00 EUR",
        source_id="assistente-locale-1",
    )
    res1 = bridge.handle(r1)
    print("Caso 1 (summarize + dati sensibili)")
    print("  decisione :", res1.decision.value)
    print("  output    :", res1.output)
    print()

    # Caso 2: operazione non whitelisted -> deny, ma comunque loggata
    r2 = BridgeRequest(
        operation=OperationType.EXTRACT,
        payload="estrai tutte le clausole riservate",
        source_id="assistente-locale-1",
    )
    res2 = bridge.handle(r2)
    print("Caso 2 (operazione non whitelisted)")
    print("  decisione :", res2.decision.value)
    print("  motivo    :", res2.denial_reason)
    print()

    # Caso 3: feature flag del provider esterno DISABILITATA -> la richiesta
    # viene respinta a valle senza toccare il resto della pipeline.
    bridge_disabled = Bridge(
        policy_engine=PolicyEngine(),
        adapter=StubExternalAdapter(),
        audit_logger=AuditLogger(LOG_PATH),
        external_provider_enabled=False,
    )
    r3 = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="Contatta anna.rossi@example.com per il rimborso di 500,00 EUR",
        source_id="assistente-locale-1",
    )
    res3 = bridge_disabled.handle(r3)
    print("Caso 3 (feature flag esterno DISABILITATO)")
    print("  decisione :", res3.decision.value)
    print("  motivo    :", res3.denial_reason)
    print()

    # Verifica integrità del log: deve risultare intatto
    ok, reason = AuditLogger(LOG_PATH).verify_integrity()
    print("Verifica integrità audit log (prima della manomissione):", ok, reason or "")
    print()

    # Mostriamo il contenuto del log: nessun payload in chiaro, solo digest
    print("Contenuto audit log:")
    for entry in AuditLogger(LOG_PATH).read_all():
        r = entry["record"]
        print(
            f"  [{r['decision']:>20}] op={r['operation']:<10} "
            f"digest={r['payload_digest'][:12]}... provider={r['provider_used']}"
        )
    print()

    # Simuliamo una manomissione: qualcuno modifica una riga vecchia a mano
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["record"]["decision"] = "allow"  # es. qualcuno nasconde un deny passato
    lines[0] = json.dumps(tampered, ensure_ascii=False)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, reason = AuditLogger(LOG_PATH).verify_integrity()
    print("Verifica integrità audit log (DOPO manomissione manuale):", ok, "|", reason)


if __name__ == "__main__":
    main()
