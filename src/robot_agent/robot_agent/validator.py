from __future__ import annotations
from typing import Any, Dict

from robot_agent.schema import (
    ALLOWED_ACTIONS,
    ALLOWED_EXECUTABLES,
    ALLOWED_INTENTS,
    ALLOWED_LAUNCH_FILES,
    ALLOWED_TARGETS,
)


MAX_DISTANCE_M = 6.0
MAX_ANGLE_DEG = 180.0
MAX_DURATION_S = 10.0
MAX_LAUNCH_ARGUMENTS = 20


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

        elif action_type == "launch_file":
            package_name = action.get("package")
            launch_file = action.get("launch_file")
            if not isinstance(package_name, str) or not package_name.strip():
                raise ValueError("launch_file action requires a non-empty package")
            if not isinstance(launch_file, str) or not launch_file.strip():
                raise ValueError("launch_file action requires a non-empty launch_file")
            package_name = package_name.strip()
            launch_file = launch_file.strip()
            if launch_file not in ALLOWED_LAUNCH_FILES.get(package_name, set()):
                raise ValueError(f"Forbidden launch file: {package_name}/{launch_file}")
            cleaned["package"] = package_name
            cleaned["launch_file"] = launch_file
            arguments = action.get("arguments")
            if arguments is not None:
                if not isinstance(arguments, list) or any(not isinstance(arg, str) for arg in arguments):
                    raise ValueError("launch_file arguments must be a list of strings")
                if len(arguments) > MAX_LAUNCH_ARGUMENTS:
                    raise ValueError("Too many launch_file arguments")
                cleaned["arguments"] = [
                    arg.strip()
                    for arg in arguments
                    if arg.strip() and "\n" not in arg and "\x00" not in arg
                ]

        elif action_type == "stop_launch":
            package_name = action.get("package")
            launch_file = action.get("launch_file")
            if package_name is not None:
                if not isinstance(package_name, str) or not package_name.strip():
                    raise ValueError("stop_launch package must be a non-empty string")
                cleaned["package"] = package_name.strip()
            if launch_file is not None:
                if not isinstance(launch_file, str) or not launch_file.strip():
                    raise ValueError("stop_launch launch_file must be a non-empty string")
                cleaned["launch_file"] = launch_file.strip()
            if "launch_file" in cleaned and "package" not in cleaned:
                raise ValueError("stop_launch launch_file requires package")
            if "package" in cleaned and "launch_file" in cleaned:
                if cleaned["launch_file"] not in ALLOWED_LAUNCH_FILES.get(cleaned["package"], set()):
                    raise ValueError(
                        f"Forbidden launch file: {cleaned['package']}/{cleaned['launch_file']}"
                    )

        elif action_type == "start_executable":
            package_name = action.get("package")
            executable = action.get("executable")
            if not isinstance(package_name, str) or not package_name.strip():
                raise ValueError("start_executable action requires a non-empty package")
            if not isinstance(executable, str) or not executable.strip():
                raise ValueError("start_executable action requires a non-empty executable")
            package_name = package_name.strip()
            executable = executable.strip()
            if executable not in ALLOWED_EXECUTABLES.get(package_name, set()):
                raise ValueError(f"Forbidden executable: {package_name}/{executable}")
            cleaned["package"] = package_name
            cleaned["executable"] = executable
            arguments = action.get("arguments")
            if arguments is not None:
                if not isinstance(arguments, list) or any(not isinstance(arg, str) for arg in arguments):
                    raise ValueError("start_executable arguments must be a list of strings")
                if len(arguments) > MAX_LAUNCH_ARGUMENTS:
                    raise ValueError("Too many start_executable arguments")
                cleaned["arguments"] = [
                    arg.strip()
                    for arg in arguments
                    if arg.strip() and "\n" not in arg and "\x00" not in arg
                ]

        elif action_type == "stop_executable":
            package_name = action.get("package")
            executable = action.get("executable")
            if not isinstance(package_name, str) or not package_name.strip():
                raise ValueError("stop_executable action requires a non-empty package")
            if not isinstance(executable, str) or not executable.strip():
                raise ValueError("stop_executable action requires a non-empty executable")
            package_name = package_name.strip()
            executable = executable.strip()
            if executable not in ALLOWED_EXECUTABLES.get(package_name, set()):
                raise ValueError(f"Forbidden executable: {package_name}/{executable}")
            cleaned["package"] = package_name
            cleaned["executable"] = executable

        target = action.get("target")
        if target is not None:
            if target not in ALLOWED_TARGETS:
                raise ValueError(f"Invalid target: {target}")
            cleaned["target"] = target

        validated_actions.append(cleaned)

    data["actions"] = validated_actions

    if data["intent"] != "robot_action":
        data["should_execute"] = False
        data["actions"] = []

    if data["should_execute"] and len(data["actions"]) == 0:
        data["should_execute"] = False

    return data
