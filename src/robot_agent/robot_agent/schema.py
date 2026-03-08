from typing import Any, Dict


ALLOWED_INTENTS = {
    "conversation",
    "robot_action",
    "clarification",
    "unsafe_or_forbidden",
}

ALLOWED_ACTIONS = {
    "move_forward",
    "move_backward",
    "turn_left",
    "turn_right",
    "stop",
    "wait",
}


def fallback_response() -> Dict[str, Any]:
    return {
        "assistant_response": "Je n'ai pas pu interpréter la demande de manière fiable.",
        "intent": "clarification",
        "should_execute": False,
        "actions": [],
    }