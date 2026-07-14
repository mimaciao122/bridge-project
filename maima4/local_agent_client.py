"""Client di riferimento minimo per un agente locale che chiama il bridge via HTTP.

Questo script mostra esattamente il contract JSON esposto dal bridge HTTP:
- `operation`
- `payload`
- `sensitivity`
- `max_output_tokens`

L'autenticazione avviene tramite header `X-Bridge-Key`; il bridge non accetta
`source_id` dalla body della richiesta, perché la sorgente viene ricavata solo
in base alla chiave.
"""

from __future__ import annotations

import json
import os
import sys
from enum import Enum
from typing import Any

import requests


class OperationType(str, Enum):
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    CLASSIFY = "classify"
    EXTRACT = "extract"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:8787/v1/bridge/request")
BRIDGE_KEY = os.environ.get("BRIDGE_KEY", "chiave-super-segreta-1")


def send_bridge_request(
    operation: OperationType,
    payload: str,
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL,
    max_output_tokens: int = 500,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Bridge-Key": BRIDGE_KEY,
    }
    body = {
        "operation": operation.value,
        "payload": payload,
        "sensitivity": sensitivity.value,
        "max_output_tokens": max_output_tokens,
    }

    response = requests.post(BRIDGE_URL, headers=headers, json=body, timeout=15)
    response.raise_for_status()
    return response.json()


def main() -> None:
    payload = "Questo è un testo di esempio con un indirizzo email mario.rossi@example.com."
    response = send_bridge_request(
        operation=OperationType.SUMMARIZE,
        payload=payload,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    print("Bridge response:")
    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
