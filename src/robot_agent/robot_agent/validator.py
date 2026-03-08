from typing import Any, Dict

from robot_agent.schema import ALLOWED_ACTIONS, ALLOWED_INTENTS


MAX_DISTANCE_M = 2.0
MAX_ANGLE_DEG = 180.0
MAX_DURATION_S = 10.0


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(float(value), max_value))


def validate_agent_output(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Output must be a dict")

    required_keys = {"assistant_response", "intent", "should_execute", "actions"}
    if set(data.keys()) != required_keys:
        raise ValueError(f"Invalid keys: {set(data.keys())}")

    if not isinstance(data["assistant_response"], str):
        raise ValueError("assistant_response must be a string")

    if data["intent"] not in ALLOWED_INTENTS:
        raise ValueError(f"Invalid intent: {data['intent']}")

    if not isinstance(data["should_execute"], bool):
        raise ValueError("should_execute must be a boolean")

    if not isinstance(data["actions"], list):
        raise ValueError("actions must be a list")

    validated_actions = []

    for action in data["actions"]:
        if not isinstance(action, dict):
            raise ValueError("Each action must be a dict")

        action_type = action.get("type")
        if action_type not in ALLOWED_ACTIONS:
            raise ValueError(f"Forbidden action: {action_type}")

        cleaned = {"type": action_type}

        if action_type in {"move_forward", "move_backward"}:
            distance = _clamp(action.get("distance_m", 0.0), 0.0, MAX_DISTANCE_M)
            cleaned["distance_m"] = distance

        elif action_type in {"turn_left", "turn_right"}:
            angle = _clamp(action.get("angle_deg", 0.0), 0.0, MAX_ANGLE_DEG)
            cleaned["angle_deg"] = angle

        elif action_type == "wait":
            duration = _clamp(action.get("duration_s", 0.0), 0.0, MAX_DURATION_S)
            cleaned["duration_s"] = duration

        validated_actions.append(cleaned)

    data["actions"] = validated_actions

    if data["intent"] != "robot_action":
        data["should_execute"] = False
        data["actions"] = []

    if data["should_execute"] and len(data["actions"]) == 0:
        data["should_execute"] = False

    return data