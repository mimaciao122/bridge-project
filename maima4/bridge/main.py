from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Quando eseguito come script con `python3 bridge/main.py`, la directory
# iniziale è `bridge/` e il pacchetto `bridge` non viene risolto.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bridge.core.config import BridgeConfig
from bridge.core.factory import create_bridge
from bridge.core.contract import BridgeRequest, OperationType, SensitivityLevel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Esegui il bridge AI con feature flag e audit")
    parser.add_argument("--operation", required=True, choices=[op.value for op in OperationType], help="Tipo di operazione")
    parser.add_argument("--payload", required=True, help="Testo in input per il bridge")
    parser.add_argument("--source-id", required=True, help="Identificativo della sorgente della richiesta")
    parser.add_argument("--sensitivity", default=SensitivityLevel.INTERNAL.value, choices=[level.value for level in SensitivityLevel], help="Livello di sensibilità del payload")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BridgeConfig.from_env()
    bridge = create_bridge(config)

    request = BridgeRequest(
        operation=OperationType(args.operation),
        payload=args.payload,
        source_id=args.source_id,
    )
    response = bridge.handle(request)

    print("Decisione:", response.decision.value)
    if response.output is not None:
        print("Output:", response.output)
    if response.denial_reason is not None:
        print("Motivo:", response.denial_reason)
    print("Provider:", response.provider_used)
    print("Latency ms:", response.latency_ms)


if __name__ == "__main__":
    main()
