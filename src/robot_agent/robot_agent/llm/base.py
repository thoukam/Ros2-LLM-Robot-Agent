from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]]) -> str:
        pass