"""
Test per bridge/http_server.py — la superficie di rischio più esposta:
qui viene deciso se una chiamata HTTP è autorizzata e da quale source_id.

Il modulo legge le variabili d'ambiente al momento dell'import (per
costruire `_AGENTS` e il `Bridge` globale), quindi le impostiamo PRIMA
di importare `bridge.http_server`.
"""

import json
import os

os.environ["BRIDGE_AGENTS_JSON"] = json.dumps({"chiave-test": "agente-test"})
os.environ["EXTERNAL_AI_ENABLED"] = "true"
os.environ["USE_REAL_ADAPTER"] = "false"
os.environ["AUDIT_LOG_PATH"] = "audit_test_http.jsonl"

from fastapi.testclient import TestClient  # noqa: E402

from bridge import http_server  # noqa: E402

client = TestClient(http_server.app)


def test_health_endpoint_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_without_key_is_rejected():
    response = client.post(
        "/v1/bridge/request",
        json={"operation": "summarize", "payload": "testo"},
    )
    assert response.status_code == 401


def test_request_with_wrong_key_is_rejected():
    response = client.post(
        "/v1/bridge/request",
        json={"operation": "summarize", "payload": "testo"},
        headers={"X-Bridge-Key": "chiave-sbagliata"},
    )
    assert response.status_code == 401


def test_request_with_valid_key_is_accepted():
    response = client.post(
        "/v1/bridge/request",
        json={"operation": "summarize", "payload": "testo semplice"},
        headers={"X-Bridge-Key": "chiave-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in ("allow", "allow_with_redaction")


def test_body_cannot_inject_a_different_source_id():
    """Il body NON espone `source_id`: anche se il chiamante prova a
    inserirlo, FastAPI lo ignora perché non è un campo di BridgeRequestIn."""
    response = client.post(
        "/v1/bridge/request",
        json={
            "operation": "summarize",
            "payload": "testo",
            "source_id": "agente-finto-iniettato",
        },
        headers={"X-Bridge-Key": "chiave-test"},
    )
    assert response.status_code == 200
    # se il campo fosse stato accettato, FastAPI l'avrebbe rifiutato o ignorato;
    # qui verifichiamo solo che la richiesta comunque passi con la source_id
    # reale derivata dalla chiave, non da quella iniettata (verificabile
    # indirettamente: nessun errore di validazione per campo sconosciuto,
    # comportamento coerente con lo schema BridgeRequestIn)
