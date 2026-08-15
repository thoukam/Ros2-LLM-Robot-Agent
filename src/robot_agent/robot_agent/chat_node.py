from __future__ import annotations

import rclpy
from rclpy.node import Node

from robot_agent.agent import ConversationalRobotAgent
from robot_agent.ros_graph import ROSGraphInspector
from robot_executor.executor_node import RobotExecutor


class ChatNode(Node):
    def __init__(self) -> None:
        super().__init__("chat_node")

        self.declare_parameter("llm_provider", "ollama")
        self.declare_parameter("llm_model", "llama3")
        self.declare_parameter("ollama_host", "http://localhost:11434")

        provider = self.get_parameter("llm_provider").value
        model = self.get_parameter("llm_model").value
        ollama_host = self.get_parameter("ollama_host").value

        self.get_logger().info(
            f"Starting chat_node with provider={provider}, model={model}"
        )

        self.robot_executor = RobotExecutor()
        self.graph_inspector = ROSGraphInspector(self)
        graph_context = self.graph_inspector.summarize_graph()

        self.agent = ConversationalRobotAgent(
            provider=provider,
            model=model,
            ollama_host=ollama_host,
            robot_context=graph_context,
        )

    def run_chat(self) -> None:
        print("Robot chat ready. Tape 'quit' pour quitter.\n")

        try:
            while rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.05)
                rclpy.spin_once(self.robot_executor, timeout_sec=0.05)
                user_message = input("You: ").strip()
                print("  ")

                if user_message.lower() in {"quit", "exit"}:
                    break

                if not user_message:
                    continue

                graph_context = self.graph_inspector.summarize_graph()
                graph_context += "\n\n" + self.graph_inspector.summarize_tf()
                graph_context += "\n\n" + self.robot_executor.get_obstacle_status()
                graph_context += "\n\n" + self.robot_executor.get_diagnostics()
                graph_context += "\n\n" + self.robot_executor.get_execution_status()
                graph_context += "\n\n" + self.robot_executor.get_motion_status()
                graph_context += "\n\n" + self.graph_inspector.summarize_rosout()
                self.agent.update_robot_context(graph_context)

                result = self.agent.run(user_message)

                if result["intent"] != "system_error":
                    print(f"Robot: {result['assistant_response']}")
                else:
                    print(f"[SYSTEM] {result['assistant_response']}")
                print("  ")

                if result["should_execute"]:
                    self.robot_executor.execute_plan(result["actions"])

        finally:
            self.robot_executor.shutdown_launch_processes()
            self.robot_executor.stop()
            self.robot_executor.destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)

    node = ChatNode()

    try:
        node.run_chat()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()