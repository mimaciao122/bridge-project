from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BridgeConfig:
    external_ai_enabled: bool = True
    use_real_adapter: bool = False
    use_real_adapter_env: str = "USE_REAL_ADAPTER"
    bridge_adapter_env: str = "BRIDGE_ADAPTER"
    adapter_name: str = "huggingface"
    external_ai_enabled_env: str = "EXTERNAL_AI_ENABLED"
    huggingface_api_key_env: str = "HUGGINGFACE_API_TOKEN"
    huggingface_model: str = "google/flan-t5-small"
    groq_api_key_env: str = "GROQ_API_KEY"
    groq_model: str = "llama-3.3-70b-versatile"
    audit_log_path: Path | str = Path("audit_test.jsonl")

    SUPPORTED_ADAPTERS: tuple[str, ...] = ("huggingface", "groq")

    @classmethod
    def _env_flag(cls, name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.lower() in ("1", "true", "yes", "on")

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        default = cls()
        use_real_adapter = cls._env_flag(default.use_real_adapter_env, default.use_real_adapter)
        adapter_name = os.environ.get(default.bridge_adapter_env, default.adapter_name).lower()
        if adapter_name not in default.SUPPORTED_ADAPTERS:
            adapter_name = default.adapter_name
        external_ai_enabled = cls._env_flag(default.external_ai_enabled_env, default.external_ai_enabled)
        huggingface_model = os.environ.get("HUGGINGFACE_MODEL", default.huggingface_model)
        groq_model = os.environ.get("GROQ_MODEL", default.groq_model)
        audit_log_path = Path(os.environ.get("AUDIT_LOG_PATH", str(default.audit_log_path)))
        return cls(
            external_ai_enabled=external_ai_enabled,
            use_real_adapter=use_real_adapter,
            adapter_name=adapter_name,
            huggingface_model=huggingface_model,
            groq_model=groq_model,
            audit_log_path=audit_log_path,
        )
