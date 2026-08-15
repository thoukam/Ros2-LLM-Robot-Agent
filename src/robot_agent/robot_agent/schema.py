from __future__ import annotations
from typing import Any, Dict

from robot_executor.software_catalog import ALLOWED_EXECUTABLES, ALLOWED_LAUNCH_FILES


ALLOWED_INTENTS = {
    "conversation",
    "robot_action",
    "clarification",
    "unsafe_or_forbidden",
    "system_error",
}

ALLOWED_ACTIONS = {
    "move_forward",
    "move_backward",
    "turn_left",
    "turn_right",
    "stop",
    "wait",
    "launch_file",
    "stop_launch",
    "start_executable",
    "stop_executable",
}

ALLOWED_TARGETS = {"robot", "mannequin"}


def fallback_response() -> Dict[str, Any]:
    return {
        "assistant_response": "Je n'ai pas pu interpréter la demande de manière fiable.",
        "intent": "clarification",
        "should_execute": False,
        "actions": [],
    }
