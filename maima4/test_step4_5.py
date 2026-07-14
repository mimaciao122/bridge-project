"""
Test manuale end-to-end per Step 4 + Step 5.
Esegui con:  python3 test_step4_5.py
(richiede: pip install pydantic)

Il log di audit viene scritto in ./audit_test_4_5.jsonl.
"""

import os
from pathlib import Path

from bridge.audit.logger import AuditLogger
from bridge.core.config import BridgeConfig
from bridge.core.factory import create_bridge
from bridge.core.contract import BridgeRequest, OperationType


LOG_PATH = Path("audit_test_4_5.jsonl")


def main() -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    config_enabled = BridgeConfig.from_env()
    bridge_enabled = create_bridge(config_enabled)

    print("=== Step 5: test con provider esterno abilitato ===")
    r1 = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="Contatta mario.rossi@example.com per il bonifico di 1.250,00 EUR",
        source_id="assistente-locale-1",
    )
    res1 = bridge_enabled.handle(r1)
    print("Caso 1")
    print("  decisione :", res1.decision.value)
    print("  output    :", res1.output)
    print("  provider  :", res1.provider_used)
    print()

    config_disabled = BridgeConfig(
        external_ai_enabled=False,
        use_real_adapter=False,
        audit_log_path=LOG_PATH,
    )
    bridge_disabled = create_bridge(config_disabled)

    print("=== Step 5: test con provider esterno disabilitato ===")
    r2 = BridgeRequest(
        operation=OperationType.SUMMARIZE,
        payload="Contatta anna.rossi@example.com per il rimborso di 500,00 EUR",
        source_id="assistente-locale-1",
    )
    res2 = bridge_disabled.handle(r2)
    print("Caso 2")
    print("  decisione :", res2.decision.value)
    print("  motivo    :", res2.denial_reason)
    print("  provider  :", res2.provider_used)
    print()

    # Verifica integrità del log
    ok, reason = AuditLogger(LOG_PATH).verify_integrity()
    print("Verifica integrità audit log:", ok, reason or "")
    print()

    # Mostriamo il contenuto del log
    print("Contenuto audit log:")
    for entry in AuditLogger(LOG_PATH).read_all():
        r = entry["record"]
        print(
            f"  [{r['decision']:>20}] op={r['operation']:<10} "
            f"digest={r['payload_digest'][:12]}... provider={r['provider_used']}"
        )
    print()

    if os.environ.get(config_enabled.huggingface_api_key_env):
        print("Chiave Hugging Face trovata. Se USE_REAL_ADAPTER=1, verrà usato il modello reale.")
    else:
        print(
            "Nessuna chiave Hugging Face trovata."
            " Con USE_REAL_ADAPTER=1 l'adapter solleverà un errore: crea un token gratuito su"
            " https://huggingface.co/settings/tokens e impostalo in HUGGINGFACE_API_TOKEN."
        )


if __name__ == "__main__":
    main()
