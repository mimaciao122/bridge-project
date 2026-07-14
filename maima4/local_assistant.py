"""Assistente locale minimo — un processo reale che gira e chiama il bridge.

Non è un mock: è un punto di partenza funzionante. Riceve un testo (da
riga di comando o interattivamente), lo impacchetta secondo il contratto
del bridge e mostra la risposta. Quando l'assistente "vero" prenderà forma
(qualunque interfaccia avrà), l'unica cosa da sostituire è "da dove arriva
il testo": la chiamata al bridge resta identica.

Uso:
    python3 local_assistant.py "Testo da riassumere con mario.rossi@example.com"
    python3 local_assistant.py                      # modalità interattiva
    python3 local_assistant.py --operation translate --sensitivity confidential "testo"
"""

from __future__ import annotations

import argparse
import json
import sys

from local_agent_client import OperationType, SensitivityLevel, send_bridge_request


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assistente locale di riferimento per il bridge")
    parser.add_argument("text", nargs="?", help="Testo da inviare al bridge. Se omesso, parte la modalità interattiva.")
    parser.add_argument(
        "--operation",
        choices=[op.value for op in OperationType],
        default=OperationType.SUMMARIZE.value,
    )
    parser.add_argument(
        "--sensitivity",
        choices=[s.value for s in SensitivityLevel],
        default=SensitivityLevel.INTERNAL.value,
    )
    parser.add_argument("--max-output-tokens", type=int, default=500)
    return parser.parse_args()


def _send(text: str, operation: str, sensitivity: str, max_output_tokens: int) -> None:
    try:
        response = send_bridge_request(
            operation=OperationType(operation),
            payload=text,
            sensitivity=SensitivityLevel(sensitivity),
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - vogliamo mostrare qualsiasi errore all'utente finale
        print(f"[assistente] Errore nel contattare il bridge: {exc}", file=sys.stderr)
        return

    print(json.dumps(response, indent=2, ensure_ascii=False))


def _interactive(operation: str, sensitivity: str, max_output_tokens: int) -> None:
    print("Assistente locale — modalità interattiva. Ctrl+C o riga vuota per uscire.")
    print(f"(operation={operation}, sensitivity={sensitivity}, max_output_tokens={max_output_tokens})\n")
    try:
        while True:
            text = input("> ").strip()
            if not text:
                break
            _send(text, operation, sensitivity, max_output_tokens)
    except (KeyboardInterrupt, EOFError):
        print("\nChiusura.")


def main() -> None:
    args = _parse_args()
    if args.text:
        _send(args.text, args.operation, args.sensitivity, args.max_output_tokens)
    else:
        _interactive(args.operation, args.sensitivity, args.max_output_tokens)


if __name__ == "__main__":
    main()
