import math
import time
from typing import Dict, List

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class RobotExecutor(Node):
    def __init__(self) -> None:
        super().__init__("robot_executor")
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.get_logger().info("Robot executor started")

    def stop(self) -> None:
        msg = Twist()
        self.cmd_pub.publish(msg)

    def publish_for_duration(
        self,
        linear_x: float = 0.0,
        angular_z: float = 0.0,
        duration: float = 0.0,
    ) -> None:
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z

        start_time = time.time()
        while time.time() - start_time < duration:
            self.cmd_pub.publish(msg)
            time.sleep(0.1)

        self.stop()

    def execute_action(self, action: Dict) -> None:
        action_type = action["type"]

        if action_type == "move_forward":
            speed = 0.15
            duration = action["distance_m"] / speed
            self.publish_for_duration(linear_x=speed, duration=duration)

        elif action_type == "move_backward":
            speed = -0.15
            duration = action["distance_m"] / abs(speed)
            self.publish_for_duration(linear_x=speed, duration=duration)

        elif action_type == "turn_left":
            angular_speed = 0.5
            duration = math.radians(action["angle_deg"]) / angular_speed
            self.publish_for_duration(angular_z=angular_speed, duration=duration)

        elif action_type == "turn_right":
            angular_speed = -0.5
            duration = math.radians(action["angle_deg"]) / abs(angular_speed)
            self.publish_for_duration(angular_z=angular_speed, duration=duration)

        elif action_type == "wait":
            time.sleep(action["duration_s"])

        elif action_type == "stop":
            self.stop()

        else:
            self.get_logger().warning(f"Unknown action type: {action_type}")

    def execute_plan(self, actions: List[Dict]) -> None:
        for action in actions:
            self.get_logger().info(f"Executing: {action}")
            self.execute_action(action)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotExecutor()

    demo_plan = [
        {"type": "move_forward", "distance_m": 0.5},
        {"type": "wait", "duration_s": 1.0},
        {"type": "turn_left", "angle_deg": 90},
        {"type": "wait", "duration_s": 1.0},
        {"type": "stop"},
    ]

    try:
        time.sleep(2.0)
        node.execute_plan(demo_plan)
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()