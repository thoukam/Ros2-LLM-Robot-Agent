import rclpy

from robot_agent.agent import ConversationalRobotAgent
from robot_executor.executor_node import RobotExecutor


def main(args=None) -> None:
    rclpy.init(args=args)

    agent = ConversationalRobotAgent()
    executor = RobotExecutor()

    print("Robot chat ready. Tape 'quit' pour quitter.\n")

    try:
        while True:
            user_message = input("You: ").strip()

            if user_message.lower() in {"quit", "exit"}:
                break

            if not user_message:
                continue

            result = agent.run(user_message)

            print(f"Robot: {result['assistant_response']}")
            print(f"Intent: {result['intent']}")
            print(f"Should execute: {result['should_execute']}")
            print(f"Actions: {result['actions']}\n")

            if result["should_execute"]:
                executor.execute_plan(result["actions"])

    finally:
        executor.stop()
        executor.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()