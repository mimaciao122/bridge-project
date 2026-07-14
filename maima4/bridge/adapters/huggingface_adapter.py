from __future__ import annotations

import json
import time
from typing import Optional

import requests

from bridge.core.contract import BridgeRequest, OperationType
from bridge.adapters.external_ai_stub import ExternalAIAdapter


class HuggingFaceAdapter(ExternalAIAdapter):
    """Adapter reale verso l'Inference API gratuita di Hugging Face.

    Usa un modello pubblico come `google/flan-t5-small`. Un token è
    praticamente sempre necessario: le chiamate anonime alla Serverless
    Inference API non sono più affidabili. Il token è comunque gratuito:
    basta un account su https://huggingface.co e un token "Read" creato su
    https://huggingface.co/settings/tokens.
    """

    name = "huggingface"

    def __init__(self, api_key: Optional[str], model: str = "google/flan-t5-small") -> None:
        if not api_key:
            raise ValueError(
                "HUGGINGFACE_API_TOKEN non fornita. Crea un token gratuito su "
                "https://huggingface.co/settings/tokens e impostala in ambiente: "
                "la Inference API richiede ormai sempre un token, anche per l'uso gratuito."
            )
        self.api_key = api_key
        self.model = model
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model}"

    def _request(self, payload: dict[str, object]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(data["error"])
        if isinstance(data, list) and data and isinstance(data[0], dict):
            if "generated_text" in data[0]:
                return data[0]["generated_text"]
            if "summary_text" in data[0]:
                return data[0]["summary_text"]
        if isinstance(data, str):
            return data

        return json.dumps(data, ensure_ascii=False)

    def call(self, request: BridgeRequest, sanitized_payload: str) -> str:
        time.sleep(0.05)
        prompt = sanitized_payload
        if request.operation == OperationType.SUMMARIZE:
            prompt = f"Summarize the following text:\n{sanitized_payload}"
        elif request.operation == OperationType.TRANSLATE:
            prompt = f"Translate the following text to English:\n{sanitized_payload}"
        elif request.operation == OperationType.CLASSIFY:
            prompt = f"Classify the following text in one short label:\n{sanitized_payload}"
        elif request.operation == OperationType.EXTRACT:
            prompt = f"Extract the most relevant information from the following text:\n{sanitized_payload}"

        return self._request({"inputs": prompt, "parameters": {"max_new_tokens": 150}})
