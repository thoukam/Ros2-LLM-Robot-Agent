# Copyright 2026 roboticslab

from robot_executor.software_catalog import (
    EXECUTABLE_COMPONENTS,
    LAUNCH_COMPONENTS,
    ROBOT_READY_NODES,
)


def test_dependent_components_require_robot_nodes():
    dependent_components = [
        LAUNCH_COMPONENTS['indoor_navigation/mapping.launch.py'],
        LAUNCH_COMPONENTS['nav2_bringup/navigation_launch.py'],
        LAUNCH_COMPONENTS['indoor_navigation/indoor_nav.launch.py'],
        LAUNCH_COMPONENTS['indoor_navigation/frontier_exploration.launch.py'],
        EXECUTABLE_COMPONENTS['rviz2/rviz2'],
    ]

    for component in dependent_components:
        assert component['required_nodes'] == ROBOT_READY_NODES


def test_robot_launch_has_no_robot_prerequisite():
    assert 'required_nodes' not in LAUNCH_COMPONENTS['robot_indoor/view.launch.py']
