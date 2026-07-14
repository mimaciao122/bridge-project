from __future__ import annotations

import json
import time
from typing import Optional

import requests

from bridge.core.contract import BridgeRequest, OperationType
from bridge.adapters.external_ai_stub import ExternalAIAdapter


class GroqAdapter(ExternalAIAdapter):
    """Adapter reale verso l'API di Groq (compatibile OpenAI, chat completions).

    Groq offre un free tier generoso e risposte molto veloci su modelli open
    (es. Llama). Serve una API key gratuita creata su
    https://console.groq.com/keys (basta un account gratuito).
    """

    name = "groq"

    def __init__(self, api_key: Optional[str], model: str = "llama-3.3-70b-versatile") -> None:
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY non fornita. Crea una API key gratuita su "
                "https://console.groq.com/keys e impostala in ambiente."
            )
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def _build_prompt(self, request: BridgeRequest, sanitized_payload: str) -> str:
        if request.operation == OperationType.SUMMARIZE:
            return f"Riassumi il seguente testo in modo conciso:\n\n{sanitized_payload}"
        if request.operation == OperationType.TRANSLATE:
            return f"Traduci il seguente testo in inglese:\n\n{sanitized_payload}"
        if request.operation == OperationType.CLASSIFY:
            return f"Classifica il seguente testo con una singola etichetta breve:\n\n{sanitized_payload}"
        if request.operation == OperationType.EXTRACT:
            return f"Estrai le informazioni più rilevanti dal seguente testo:\n\n{sanitized_payload}"
        return sanitized_payload

    def _request(self, prompt: str, max_output_tokens: int) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output_tokens,
        }

        response = requests.post(self.endpoint, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(data["error"])

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return json.dumps(data, ensure_ascii=False)

    def call(self, request: BridgeRequest, sanitized_payload: str) -> str:
        time.sleep(0.05)
        prompt = self._build_prompt(request, sanitized_payload)
        max_tokens = min(request.max_output_tokens, 4000) if request.max_output_tokens else 500
        return self._request(prompt, max_tokens)
