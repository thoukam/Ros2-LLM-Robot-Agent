from __future__ import annotations

from typing import Dict, List, Set, TypedDict


class LaunchSpec(TypedDict, total=False):
    label: str
    command: List[str]
    nodes: Set[str]
    required_nodes: Set[str]


class ExecutableSpec(TypedDict, total=False):
    label: str
    command: List[str]
    nodes: Set[str]
    required_nodes: Set[str]


ROBOT_READY_NODES = {'robot_state_publisher', 'parameter_bridge'}


LAUNCH_COMPONENTS: Dict[str, LaunchSpec] = {
    'gazebo_ros_actor_plugin/sim.launch.py': {
        'label': 'simulation Gazebo avec acteur',
        'command': ['ros2', 'launch', 'gazebo_ros_actor_plugin', 'sim.launch.py'],
        'nodes': {'gazebo_ros_actor_command'},
    },
    'robot_indoor/view.launch.py': {
        'label': 'robot dans Gazebo',
        'command': ['ros2', 'launch', 'robot_indoor', 'view.launch.py'],
        'nodes': {
            'robot_state_publisher',
            'joint_state_publisher',
            'parameter_bridge',
            'image_bridge',
        },
    },
    'indoor_navigation/mapping.launch.py': {
        'label': 'cartographie SLAM',
        'command': ['ros2', 'launch', 'indoor_navigation', 'mapping.launch.py'],
        'nodes': {'slam_toolbox'},
        'required_nodes': ROBOT_READY_NODES,
    },
    'nav2_bringup/navigation_launch.py': {
        'label': 'Nav2',
        'command': ['ros2', 'launch', 'nav2_bringup', 'navigation_launch.py'],
        'required_nodes': ROBOT_READY_NODES,
        'nodes': {
            'controller_server',
            'planner_server',
            'smoother_server',
            'behavior_server',
            'bt_navigator',
            'waypoint_follower',
            'velocity_smoother',
            'lifecycle_manager_navigation',
        },
    },
    'indoor_navigation/indoor_nav.launch.py': {
        'label': 'navigation indoor',
        'command': ['ros2', 'launch', 'indoor_navigation', 'indoor_nav.launch.py'],
        'required_nodes': ROBOT_READY_NODES,
        'nodes': {
            'controller_server',
            'planner_server',
            'smoother_server',
            'behavior_server',
            'bt_navigator',
            'waypoint_follower',
            'velocity_smoother',
            'lifecycle_manager_navigation',
            'rviz2',
            'base_to_map',
        },
    },
    'indoor_navigation/frontier_exploration.launch.py': {
        'label': 'explorateur autonome',
        'command': [
            'ros2',
            'launch',
            'indoor_navigation',
            'frontier_exploration.launch.py',
        ],
        'nodes': {
            'frontier_explorer',
            'slam_toolbox',
            'controller_server',
            'planner_server',
            'smoother_server',
            'behavior_server',
            'bt_navigator',
            'waypoint_follower',
            'velocity_smoother',
            'lifecycle_manager_navigation',
            'rviz2',
        },
        'required_nodes': ROBOT_READY_NODES,
    },
}


EXECUTABLE_COMPONENTS: Dict[str, ExecutableSpec] = {
    'rviz2/rviz2': {
        'label': 'RViz2',
        'command': ['rviz2'],
        'nodes': {'rviz2'},
        'required_nodes': ROBOT_READY_NODES,
    },
}


ALLOWED_LAUNCH_FILES: Dict[str, Set[str]] = {}
for component_key in LAUNCH_COMPONENTS:
    package_name, launch_file = component_key.split('/', 1)
    ALLOWED_LAUNCH_FILES.setdefault(package_name, set()).add(launch_file)


ALLOWED_EXECUTABLES: Dict[str, Set[str]] = {}
for component_key in EXECUTABLE_COMPONENTS:
    package_name, executable = component_key.split('/', 1)
    ALLOWED_EXECUTABLES.setdefault(package_name, set()).add(executable)
