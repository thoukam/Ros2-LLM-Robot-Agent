from __future__ import annotations
from typing import Dict, List
import os

from robot_agent.llm.base import BaseLLMProvider


class MistralProvider(BaseLLMProvider):
    def __init__(self, model: str) -> None:
        try:
            from mistralai.client import Mistral
        except ImportError as e:
            raise RuntimeError(
                "Le package mistralai n'est pas installé ou incompatible. "
                "Installe-le avec: pip install mistralai"
            ) from e

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is missing")

        self.client = Mistral(api_key=api_key)
        self.model = model

    def generate(self, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""