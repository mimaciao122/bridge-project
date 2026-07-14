"""
Adapter verso il sistema AI esterno.

STEP 1: è solo uno STUB. Nessuna chiamata di rete reale.
Serve a validare il contratto e il flusso end-to-end senza toccare
alcun provider vero, e senza alcun rischio di fuga dati.

Quando arriveremo allo Step 4 (adapter reale), questo file sarà sostituito
da un'implementazione che chiama davvero un provider (es. Hugging Face
Inference API), ma l'interfaccia `ExternalAIAdapter.call()` resterà identica: è il contratto
verso il resto del bridge, e non deve rompersi quando cambia il provider.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from bridge.core.contract import BridgeRequest, OperationType


class ExternalAIAdapter(ABC):
    """Interfaccia stabile: qualunque provider reale la implementa."""

    name: str

    @abstractmethod
    def call(self, request: BridgeRequest, sanitized_payload: str) -> str:
        """Riceve SOLO il payload già passato dal policy engine
        (whitelisting + eventuale redazione già avvenuti a monte).
        Ritorna il testo di output."""
        raise NotImplementedError


class StubExternalAdapter(ExternalAIAdapter):
    """Implementazione finta: non contatta nessun servizio esterno.
    Utile per testare tutta la pipeline (contratto, policy, audit)
    prima di introdurre una dipendenza di rete reale."""

    name = "external_stub"

    def call(self, request: BridgeRequest, sanitized_payload: str) -> str:
        # piccola latenza simulata, per rendere i test di audit realistici
        time.sleep(0.01)

        if request.operation == OperationType.SUMMARIZE:
            return f"[STUB summary] {sanitized_payload[:80]}..."
        if request.operation == OperationType.TRANSLATE:
            return f"[STUB translation] {sanitized_payload}"
        if request.operation == OperationType.CLASSIFY:
            return "[STUB classification] categoria=generico"
        if request.operation == OperationType.EXTRACT:
            return "[STUB extraction] nessun campo reale estratto (stub)"

        # non dovrebbe mai arrivare qui se il policy engine ha già filtrato,
        # ma teniamo un fallback esplicito e non silenzioso
        raise ValueError(f"Operazione non gestita dallo stub: {request.operation}")
