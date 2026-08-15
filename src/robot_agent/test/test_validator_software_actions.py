# Copyright 2026 roboticslab

import pytest

from robot_agent.validator import validate_agent_output


def _payload(action):
    return {
        'assistant_response': 'ok',
        'intent': 'robot_action',
        'should_execute': True,
        'actions': [action],
    }


def test_validator_accepts_allowed_software_actions():
    actions = [
        {
            'type': 'launch_file',
            'package': 'robot_indoor',
            'launch_file': 'view.launch.py',
        },
        {
            'type': 'launch_file',
            'package': 'nav2_bringup',
            'launch_file': 'navigation_launch.py',
        },
        {
            'type': 'start_executable',
            'package': 'rviz2',
            'executable': 'rviz2',
        },
        {
            'type': 'stop_executable',
            'package': 'rviz2',
            'executable': 'rviz2',
        },
    ]

    for action in actions:
        validated = validate_agent_output(_payload(action))
        assert validated['actions'] == [action]


def test_validator_rejects_unapproved_software_actions():
    actions = [
        {
            'type': 'launch_file',
            'package': 'nav2_bringup',
            'launch_file': 'bringup_launch.py',
        },
        {
            'type': 'start_executable',
            'package': 'bash',
            'executable': 'bash',
        },
        {
            'type': 'stop_launch',
            'launch_file': 'mapping.launch.py',
        },
    ]

    for action in actions:
        with pytest.raises(ValueError):
            validate_agent_output(_payload(action))
