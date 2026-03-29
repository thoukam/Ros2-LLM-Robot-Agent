from __future__ import annotations
from typing import Dict, List
import requests

from robot_agent.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str, host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host.rstrip("/")

    def generate(self, messages: List[Dict[str, str]]) -> str:
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]