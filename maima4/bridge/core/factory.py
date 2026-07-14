from __future__ import annotations

import os
from pathlib import Path

from bridge.adapters.huggingface_adapter import HuggingFaceAdapter
from bridge.adapters.groq_adapter import GroqAdapter
from bridge.adapters.external_ai_stub import StubExternalAdapter
from bridge.audit.logger import AuditLogger
from bridge.core.config import BridgeConfig
from bridge.core.orchestrator import Bridge
from bridge.policy.engine import PolicyEngine


def create_bridge(config: BridgeConfig | None = None) -> Bridge:
    config = config or BridgeConfig.from_env()
    if config.use_real_adapter:
        if config.adapter_name == "groq":
            adapter = GroqAdapter(
                api_key=os.environ.get(config.groq_api_key_env),
                model=config.groq_model,
            )
        else:
            adapter = HuggingFaceAdapter(
                api_key=os.environ.get(config.huggingface_api_key_env),
                model=config.huggingface_model,
            )
    else:
        adapter = StubExternalAdapter()

    return Bridge(
        policy_engine=PolicyEngine(),
        adapter=adapter,
        audit_logger=AuditLogger(Path(config.audit_log_path)),
        external_provider_enabled=config.external_ai_enabled,
    )
