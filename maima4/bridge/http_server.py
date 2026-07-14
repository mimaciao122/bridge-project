from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bridge.core.config import BridgeConfig
from bridge.core.factory import create_bridge
from bridge.core.contract import (
    BridgeRequest,
    BridgeResponse,
    OperationType,
    SensitivityLevel,
)


# ---------------------------------------------------------------------------
# Identità degli agenti locali autorizzati
# ---------------------------------------------------------------------------
# Formato env var BRIDGE_AGENTS_JSON: {"<api_key>": "<source_id>", ...}
# Ogni agente locale ha la propria chiave. Aggiungere un nuovo agente è
# una modifica di configurazione, non di codice.

def _load_agents() -> dict[str, str]:
    raw = os.environ.get("BRIDGE_AGENTS_JSON")
    if not raw:
        raise RuntimeError(
            "BRIDGE_AGENTS_JSON non impostata: nessun agente locale è "
            "autorizzato a chiamare il bridge. Il servizio si rifiuta di "
            "partire in questo stato, per non esporre un endpoint aperto."
        )
    return json.loads(raw)


_AGENTS = _load_agents()
_bridge = create_bridge(BridgeConfig.from_env())

app = FastAPI(title="Local AI Bridge", version="1.0")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Pagina principale: reindirizza alla mini-UI di test in /static/index.html.
    Prima non esisteva alcuna rotta su '/', da cui il 404 visto nel browser."""
    return RedirectResponse(url="/static/index.html")


def _authenticate(x_bridge_key: Optional[str]) -> str:
    """Ritorna il source_id associato alla chiave, o rifiuta la richiesta.
    Uso compare_digest per evitare timing attack sulla chiave, anche se
    l'endpoint è solo locale — è comunque una superficie di attacco."""
    if not x_bridge_key:
        raise HTTPException(status_code=401, detail="Header X-Bridge-Key mancante")
    for key, source_id in _AGENTS.items():
        if secrets.compare_digest(x_bridge_key, key):
            return source_id
    raise HTTPException(status_code=401, detail="API key non valida")


class BridgeRequestIn(BaseModel):
    """Schema esposto all'esterno. Volutamente NON include source_id:
    quello arriva solo dall'autenticazione, mai dal chiamante."""

    operation: OperationType
    payload: str
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    max_output_tokens: int = 500


@app.post("/v1/bridge/request", response_model=BridgeResponse)
def handle_request(
    body: BridgeRequestIn,
    x_bridge_key: Optional[str] = Header(default=None),
) -> BridgeResponse:
    source_id = _authenticate(x_bridge_key)

    request = BridgeRequest(
        operation=body.operation,
        payload=body.payload,
        sensitivity=body.sensitivity,
        max_output_tokens=body.max_output_tokens,
        source_id=source_id,
    )
    return _bridge.handle(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
