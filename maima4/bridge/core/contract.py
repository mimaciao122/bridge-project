"""
Contratto stabile tra:
  - assistente locale  -> bridge
  - bridge             -> adapter esterno (AI provider)

Questo schema NON deve cambiare quando cambiano i provider o l'assistente.
Chi cambia, cambia dietro questo contratto (pattern adapter / porta-e-adattatore).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    """Whitelist chiusa delle operazioni che il bridge può instradare.
    Aggiungere un valore qui è un cambiamento esplicito e consapevole,
    non un default implicito."""

    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    CLASSIFY = "classify"
    EXTRACT = "extract"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class BridgeRequest(BaseModel):
    """Richiesta che l'assistente locale invia al bridge.
    Non contiene mai credenziali esterne: quelle vivono solo dentro l'adapter."""

    request_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    operation: OperationType
    payload: str  # testo grezzo in input, prima di eventuale redazione
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL

    # metadati di provenienza, per audit e per policy (es. rate limit per source_id)
    source_id: str
    max_output_tokens: int = Field(default=500, le=4000)

    model_config = ConfigDict(frozen=True)


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_REDACTION = "allow_with_redaction"
    DENY = "deny"


class BridgeResponse(BaseModel):
    """Risposta che il bridge restituisce all'assistente locale.
    Uniforme sia in caso di successo che di blocco: l'assistente locale
    gestisce sempre lo stesso shape, non deve fare branching complesso."""

    request_id: UUID
    decision: PolicyDecision
    output: Optional[str] = None
    denial_reason: Optional[str] = None
    provider_used: Optional[str] = None  # es. "external_stub", "huggingface", ecc.
    latency_ms: Optional[int] = None

    model_config = ConfigDict(frozen=True)


class AuditRecord(BaseModel):
    """Record scritto in modo indipendente dal flusso principale.
    Deve poter essere ricostruito anche se il bridge stesso ha un bug."""

    record_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    source_id: str
    operation: OperationType
    decision: PolicyDecision
    denial_reason: Optional[str] = None

    # non salviamo mai il payload originale in chiaro nell'audit se è confidenziale:
    # solo un digest, per non duplicare il rischio nel log stesso
    payload_digest: str
    payload_length: int

    provider_used: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)
