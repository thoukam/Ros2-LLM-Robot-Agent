from __future__ import annotations
import json
from typing import Dict, List

from robot_agent.prompts import SYSTEM_PROMPT
from robot_agent.schema import fallback_response
from robot_agent.validator import validate_agent_output
from robot_agent.llm.factory import create_llm_provider


class ConversationalRobotAgent:
    def __init__(self, provider: str, model: str, ollama_host: str = "http://localhost:11434") -> None:
        self.client = create_llm_provider(
            provider=provider,
            model=model,
            ollama_host=ollama_host,
        )
        self.history: List[Dict[str, str]] = []

    def run(self, user_message: str) -> Dict:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": user_message})

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