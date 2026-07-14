"""
Orchestratore del bridge — il punto che collega i pezzi degli step 1-3:
  1. valuta la richiesta con il policy engine
  2. se permessa, chiama l'adapter esterno (oggi: lo stub)
  3. registra SEMPRE un AuditRecord, che la richiesta sia stata
     accettata o negata

Questo file non contiene logica di whitelist/redazione/rate-limit
(quella è tutta in policy/engine.py) né logica di chiamata esterna
(quella è in adapters/): qui c'è solo l'orchestrazione, per restare
sostituibile e testabile pezzo per pezzo.
"""

from __future__ import annotations

import time

from bridge.adapters.external_ai_stub import ExternalAIAdapter
from bridge.audit.logger import AuditLogger, payload_digest
from bridge.core.contract import AuditRecord, BridgeRequest, BridgeResponse, PolicyDecision
from bridge.policy.engine import PolicyEngine


class Bridge:
    def __init__(
        self,
        policy_engine: PolicyEngine,
        adapter: ExternalAIAdapter,
        audit_logger: AuditLogger,
        external_provider_enabled: bool = True,
    ) -> None:
        self._policy = policy_engine
        self._adapter = adapter
        self._audit = audit_logger
        self._external_provider_enabled = external_provider_enabled

    def handle(self, request: BridgeRequest) -> BridgeResponse:
        start = time.monotonic()

        result = self._policy.evaluate(request)

        output: str | None = None
        provider_used: str | None = None
        decision = result.decision
        denial_reason = result.denial_reason

        if result.decision in (PolicyDecision.ALLOW, PolicyDecision.ALLOW_WITH_REDACTION):
            if self._external_provider_enabled:
                # invariante di sicurezza: al provider esterno arriva SOLO il
                # payload già passato dal policy engine (redatto se necessario),
                # mai request.payload grezzo
                assert result.sanitized_payload is not None
                try:
                    output = self._adapter.call(request, result.sanitized_payload)
                    provider_used = self._adapter.name
                except Exception as exc:
                    decision = PolicyDecision.DENY
                    denial_reason = f"External provider call failed: {exc}"
                    provider_used = self._adapter.name
            else:
                decision = PolicyDecision.DENY
                denial_reason = "External provider disabled by feature flag"
                provider_used = "external_disabled"

        latency_ms = int((time.monotonic() - start) * 1000)

        response = BridgeResponse(
            request_id=request.request_id,
            decision=decision,
            output=output,
            denial_reason=denial_reason,
            provider_used=provider_used,
            latency_ms=latency_ms,
        )

        # l'audit si scrive SEMPRE, anche sui deny, e non contiene mai
        # il payload originale in chiaro
        audit_record = AuditRecord(
            request_id=request.request_id,
            source_id=request.source_id,
            operation=request.operation,
            decision=decision,
            denial_reason=denial_reason,
            payload_digest=payload_digest(request.payload),
            payload_length=len(request.payload),
            provider_used=provider_used,
            extra={"redacted_fields": result.redacted_fields, "latency_ms": latency_ms},
        )
        self._audit.append(audit_record)

        return response
