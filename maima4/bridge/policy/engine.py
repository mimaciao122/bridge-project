"""
Policy engine: l'unico punto in cui si decide se, come e quanto
una richiesta può uscire verso il sistema AI esterno.

Tre controlli, in sequenza, e nell'ordine giusto:
  1. Whitelist   -> l'operazione richiesta è permessa? (fail fast, prima di tutto)
  2. Rate limit  -> questa source_id sta chiedendo troppo/troppo spesso?
  3. Redazione   -> il contenuto va ripulito prima di lasciare il perimetro?

Se un controllo nega, i successivi non vengono nemmeno eseguiti:
niente redazione "inutile" su una richiesta già bloccata, per non
processare dati sensibili più del necessario.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from bridge.core.contract import BridgeRequest, OperationType, PolicyDecision


# ---------------------------------------------------------------------------
# 1. Whitelist
# ---------------------------------------------------------------------------

# Operazioni concesse verso l'esterno OGGI. Ampliare questa lista è una
# decisione esplicita (vedi step 3 del piano: "ampliamento gradiale"),
# non un effetto collaterale di un cambiamento altrove.
ALLOWED_OPERATIONS: set[OperationType] = {
    OperationType.SUMMARIZE,
}


def check_whitelist(request: BridgeRequest) -> tuple[bool, str | None]:
    if request.operation in ALLOWED_OPERATIONS:
        return True, None
    return False, f"Operazione '{request.operation.value}' non in whitelist esterna"


# ---------------------------------------------------------------------------
# 2. Rate / volume limiting
# ---------------------------------------------------------------------------

class RateLimiterInterface(ABC):
    """Interfaccia di rate limiting sostituibile.

    Il bridge usa sempre `allow()`. Lo stato può essere in-memory, su Redis,
    su un datastore locale o su un servizio esterno. La logica del bridge non
    dipende dalla scelta dell'implementazione.
    """

    @abstractmethod
    def allow(self, source_id: str, payload_len: int) -> tuple[bool, str | None]:
        raise NotImplementedError


@dataclass
class InMemoryRateLimiter(RateLimiterInterface):
    """Rate limiter a finestra scorrevole, per source_id.

    In-memory: sufficiente per lo Step 2. Se in futuro il bridge gira su più
    processi/nodi, basta sostituire l'implementazione con una che usa Redis,
    database o un servizio condiviso.
    """

    max_requests: int = 20
    window_seconds: float = 60.0
    max_payload_chars_per_window: int = 20_000

    _requests: dict[str, Deque[float]] = field(default_factory=dict)
    _chars: dict[str, Deque[tuple[float, int]]] = field(default_factory=dict)

    def _prune(self, dq: Deque, now: float) -> None:
        while dq and now - (dq[0] if isinstance(dq[0], float) else dq[0][0]) > self.window_seconds:
            dq.popleft()

    def allow(self, source_id: str, payload_len: int) -> tuple[bool, str | None]:
        now = time.monotonic()

        req_dq = self._requests.setdefault(source_id, deque())
        self._prune(req_dq, now)
        if len(req_dq) >= self.max_requests:
            return False, (
                f"Rate limit superato: max {self.max_requests} richieste "
                f"ogni {int(self.window_seconds)}s per source_id='{source_id}'"
            )

        char_dq = self._chars.setdefault(source_id, deque())
        self._prune(char_dq, now)
        total_chars = sum(c for _, c in char_dq) + payload_len
        if total_chars > self.max_payload_chars_per_window:
            return False, (
                f"Volume limit superato: max {self.max_payload_chars_per_window} "
                f"caratteri ogni {int(self.window_seconds)}s per source_id='{source_id}'"
            )

        req_dq.append(now)
        char_dq.append((now, payload_len))
        return True, None


class RateLimiter(InMemoryRateLimiter):
    """Alias mantenuto per compatibilità con i test e con il codice esistente."""
    pass


def _compile_patterns(patterns: dict[str, str | re.Pattern]) -> dict[str, re.Pattern]:
    compiled: dict[str, re.Pattern] = {}
    for label, pattern in patterns.items():
        compiled[label] = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)
    return compiled


_BUILTIN_PATTERNS: dict[str, re.Pattern] = _compile_patterns({
    "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
    "TELEFONO": r"\b(?:\+39\s?)?\d{2,4}[\s.-]?\d{6,8}\b",
    "IMPORTO": r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s?(?:€|EUR)\b",
    "CF": r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b",
})

_CUSTOM_PATTERNS: dict[str, re.Pattern] = {}


def register_redaction_pattern(label: str, pattern: str | re.Pattern) -> None:
    """Registra un pattern di redazione aggiuntivo, ad esempio per un dominio.

    Questo è un punto di estensione esplicito: il bridge può essere configurato
    con nuove regole di redazione senza cambiare la logica centrale.
    """
    if label in _BUILTIN_PATTERNS:
        raise ValueError(f"Label di redazione riservata: {label}")
    _CUSTOM_PATTERNS[label] = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)


def clear_custom_redaction_patterns() -> None:
    _CUSTOM_PATTERNS.clear()


def redact(text: str, extra_patterns: dict[str, str | re.Pattern] | None = None) -> tuple[str, list[str]]:
    """Ritorna il testo redatto e i tipi di dato rimossi.

    Supporta sia i pattern built-in sia le estensioni custom fornite a runtime.
    """
    patterns = dict(_BUILTIN_PATTERNS)
    patterns.update(_CUSTOM_PATTERNS)
    if extra_patterns:
        patterns.update(_compile_patterns(extra_patterns))

    redacted = text
    found: list[str] = []
    for label, pattern in patterns.items():
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(f"[REDATTO:{label}]", redacted)
    return redacted, found


# ---------------------------------------------------------------------------
# Orchestrazione: il punto unico chiamato dal bridge core
# ---------------------------------------------------------------------------

@dataclass
class PolicyResult:
    decision: PolicyDecision
    sanitized_payload: str | None
    denial_reason: str | None
    redacted_fields: list[str]


class PolicyEngine:
    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter or RateLimiter()

    def evaluate(self, request: BridgeRequest) -> PolicyResult:
        ok, reason = check_whitelist(request)
        if not ok:
            return PolicyResult(PolicyDecision.DENY, None, reason, [])

        ok, reason = self._rate_limiter.allow(request.source_id, len(request.payload))
        if not ok:
            return PolicyResult(PolicyDecision.DENY, None, reason, [])

        sanitized, found = redact(request.payload)
        decision = (
            PolicyDecision.ALLOW_WITH_REDACTION if found else PolicyDecision.ALLOW
        )
        return PolicyResult(decision, sanitized, None, found)
