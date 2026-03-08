import json
import os
from typing import Dict, List

from openai import OpenAI

from robot_agent.prompts import SYSTEM_PROMPT
from robot_agent.schema import fallback_response
from robot_agent.validator import validate_agent_output


class ConversationalRobotAgent:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")

        self.client = OpenAI(api_key=api_key)
        self.history: List[Dict[str, str]] = []

    def run(self, user_message: str) -> Dict:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0,
                response_format={"type": "json_object"},
                messages=messages,
            )

            raw = response.choices[0].message.content
            print("\n[DEBUG] Raw model output:")
            print(raw)
            print()

            parsed = json.loads(raw)
            validated = validate_agent_output(parsed)

            self.history.append({"role": "user", "content": user_message})
            self.history.append(
                {"role": "assistant", "content": json.dumps(validated, ensure_ascii=False)}
            )

            return validated

        except Exception as e:
            print(f"\n[ERROR] OpenAI/agent error: {repr(e)}\n")

            fallback = fallback_response()
            fallback["assistant_response"] = (
                "Je n'ai pas pu interpréter ta demande de manière fiable. Reformule simplement."
            )
            return fallback