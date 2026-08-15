from __future__ import annotations
import json
import re
from typing import Dict, List

from robot_agent.prompts import SYSTEM_PROMPT
from robot_agent.project_context import PROJECT_CONTEXT
from robot_agent.schema import fallback_response
from robot_agent.validator import validate_agent_output
from robot_agent.llm.factory import create_llm_provider


class ConversationalRobotAgent:
    def __init__(
        self,
        provider: str,
        model: str,
        ollama_host: str = "http://localhost:11434",
        robot_context: str = "",
    ) -> None:
        self.client = create_llm_provider(
            provider=provider,
            model=model,
            ollama_host=ollama_host,
        )
        self.history: List[Dict[str, str]] = []
        self.robot_context = robot_context

    def update_robot_context(self, robot_context: str) -> None:
        self.robot_context = robot_context

    def _build_system_prompt(self) -> str:
        base_prompt = f"{SYSTEM_PROMPT}\n\n{PROJECT_CONTEXT}"
        if not self.robot_context:
            return base_prompt

        return (
            f"{base_prompt}\n\n"
            "État actuel du graph ROS2 :\n"
            f"{self.robot_context}"
        )

    def _normalize_user_message(self, user_message: str) -> str:
        normalized = user_message
        normalized = re.sub(
            r"\b([0-9]+(?:[\.,][0-9]+)?)\s*(?:m|mètre|metre|mettre)s?\b",
            r"\1 mètres",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"\b([0-9]+)m\b", r"\1 mètres", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\b([0-9]+)\s*mettre\b", r"\1 mètres", normalized, flags=re.IGNORECASE)
        return normalized

    def run(self, user_message: str) -> Dict:
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self.history[-12:])
        normalized_message = self._normalize_user_message(user_message)
        messages.append({"role": "user", "content": normalized_message})

        try:
            raw = self.client.generate(messages)
            parsed = json.loads(raw)
            validated = validate_agent_output(parsed)

            self.history.append({"role": "user", "content": user_message})
            self.history.append(
                {"role": "assistant", "content": json.dumps(validated, ensure_ascii=False)}
            )

            return validated

        except Exception as e:
            print(f"\n[ERROR] LLM/agent error: {repr(e)}\n")

            fallback = fallback_response()
            fallback["assistant_response"] = (
                "Je n'ai pas pu interpréter ta demande de manière fiable. Reformule simplement."
            )
            return fallback