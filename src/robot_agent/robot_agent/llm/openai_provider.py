from __future__ import annotations
from typing import Dict, List
import os

from openai import OpenAI

from robot_agent.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model: str) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, messages: List[Dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            #temperature=0,
            response_format={"type": "json_object"},
            messages=messages,
        )
        return response.choices[0].message.content or ""