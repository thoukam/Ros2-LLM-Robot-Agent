import math
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from rclpy.node import Node

from robot_executor.software_catalog import (
    EXECUTABLE_COMPONENTS,
    LAUNCH_COMPONENTS,
)


class RobotExecutor(Node):
    def __init__(self) -> None:
        super().__init__("robot_executor")
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.actor_pub = self.create_publisher(Twist, "/actor/cmd_vel", 10)
        self.scan_sub = self.create_subscription(LaserScan, "/scan", self.scan_callback, 10)

        self.obstacle_threshold_m = 0.2
        self.closest_obstacle_m = float("inf")
        self.front_distance_m = float("inf")
        self.rear_distance_m = float("inf")
        self.left_distance_m = float("inf")
        self.right_distance_m = float("inf")
        self.last_obstacle_report = "Aucun obstacle détecté."
        self.last_action_attempt = "Aucune action exécutée récemment."
        self.last_diagnostic_message = "Système opérationnel. Aucun problème détecté."
        self.launch_processes: Dict[str, subprocess.Popen] = {}
        self.is_executing = False

        self.get_logger().info("Robot executor started with obstacle guard")

    def stop(self, target: str = "robot") -> None:
        msg = Twist()
        if target == "mannequin":
            self.actor_pub.publish(msg)
        else:
            self.cmd_pub.publish(msg)

    def launch_file(
        self,
        package: str,
        launch_file: str,
        arguments: Optional[List[str]] = None,
    ) -> None:
        key = self._launch_key(package, launch_file)
        component = LAUNCH_COMPONENTS.get(key)
        if component is None:
            self.last_diagnostic_message = (
                f"Launch refusé car non autorisé : {package}/{launch_file}."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        self._cleanup_finished_launches()
        if key in self.launch_processes:
            self.last_diagnostic_message = f"Launch déjà actif : {key}."
            self.get_logger().info(self.last_diagnostic_message)
            return

        missing_nodes = self._missing_required_nodes(component.get("required_nodes", set()))
        if missing_nodes:
            self.last_diagnostic_message = (
                f"Lancement refusé pour {key} : le robot doit être lancé avant cette brique. "
                f"Nœud(s) robot manquant(s) : {', '.join(missing_nodes)}. "
                "Lance d'abord robot_indoor/view.launch.py."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        conflict_nodes = self._active_conflict_nodes(component["nodes"])
        if conflict_nodes:
            self.last_diagnostic_message = (
                f"Lancement refusé pour {key} : nœud(s) déjà actif(s) "
                f"{', '.join(conflict_nodes)}. Je ne relance pas une brique déjà présente."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        command = list(component["command"])
        if arguments:
            command.extend(arguments)
        log_path = self._log_path_for_process(key)

        self.get_logger().info(
            f"Lancement du launch file : {' '.join(command)}"
        )
        try:
            with log_path.open("ab") as log_file:
                proc = subprocess.Popen(
                    command,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=os.environ.copy(),
                )
            self.launch_processes[key] = proc
            self.last_action_attempt = f"launch_file package={package} launch_file={launch_file}"
            self.last_diagnostic_message = (
                f"Launch file {launch_file} démarré pour le package {package}. "
                f"Logs : {log_path}."
            )
        except FileNotFoundError:
            self.last_diagnostic_message = (
                "Impossible de lancer le fichier : commande `ros2` introuvable."
            )
            self.get_logger().error(self.last_diagnostic_message)
        except Exception as exc:
            self.last_diagnostic_message = (
                f"Erreur lors du lancement de {package}/{launch_file} : {exc}"
            )
            self.get_logger().error(self.last_diagnostic_message)

    def _launch_key(self, package: str, launch_file: str) -> str:
        return f"{package}/{launch_file}"

    def _executable_key(self, package: str, executable: str) -> str:
        return f"{package}/{executable}"

    def _log_path_for_process(self, key: str) -> Path:
        safe_name = key.replace("/", "_").replace(".", "_")
        return Path("/tmp") / f"rosagent_launch_{safe_name}.log"

    def _active_ros_node_names(self) -> set[str]:
        names = set(self.get_node_names())
        for node_name, namespace in self.get_node_names_and_namespaces():
            names.add(node_name)
            if namespace and namespace != "/":
                names.add(f"{namespace.rstrip('/')}/{node_name}")
            else:
                names.add(f"/{node_name}")
        return names

    def _active_conflict_nodes(self, expected_nodes: set[str]) -> List[str]:
        active_nodes = self._active_ros_node_names()
        return sorted(node for node in expected_nodes if node in active_nodes)

    def _missing_required_nodes(self, required_nodes: set[str]) -> List[str]:
        active_nodes = self._active_ros_node_names()
        return sorted(node for node in required_nodes if node not in active_nodes)

    def _cleanup_finished_launches(self) -> None:
        finished = [
            key for key, proc in self.launch_processes.items()
            if proc.poll() is not None
        ]
        for key in finished:
            self.launch_processes.pop(key, None)

    def get_launch_status(self) -> str:
        self._cleanup_finished_launches()
        if not self.launch_processes:
            return "Aucune brique logicielle active."
        active = ", ".join(sorted(self.launch_processes))
        return f"Briques logicielles actives : {active}."

    def start_executable(
        self,
        package: str,
        executable: str,
        arguments: Optional[List[str]] = None,
    ) -> None:
        key = self._executable_key(package, executable)
        component = EXECUTABLE_COMPONENTS.get(key)
        if component is None:
            self.last_diagnostic_message = (
                f"Exécutable refusé car non autorisé : {package}/{executable}."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        self._cleanup_finished_launches()
        if key in self.launch_processes:
            self.last_diagnostic_message = f"Exécutable déjà actif : {key}."
            self.get_logger().info(self.last_diagnostic_message)
            return

        missing_nodes = self._missing_required_nodes(component.get("required_nodes", set()))
        if missing_nodes:
            self.last_diagnostic_message = (
                f"Lancement refusé pour {key} : le robot doit être lancé avant cette brique. "
                f"Nœud(s) robot manquant(s) : {', '.join(missing_nodes)}. "
                "Lance d'abord robot_indoor/view.launch.py."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        conflict_nodes = self._active_conflict_nodes(component["nodes"])
        if conflict_nodes:
            self.last_diagnostic_message = (
                f"Lancement refusé pour {key} : nœud(s) déjà actif(s) "
                f"{', '.join(conflict_nodes)}. Je ne relance pas une brique déjà présente."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return

        command = list(component["command"])
        if arguments:
            command.extend(arguments)
        log_path = self._log_path_for_process(key)

        self.get_logger().info(f"Lancement de l'exécutable : {' '.join(command)}")
        try:
            with log_path.open("ab") as log_file:
                proc = subprocess.Popen(
                    command,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=os.environ.copy(),
                )
            self.launch_processes[key] = proc
            self.last_action_attempt = (
                f"start_executable package={package} executable={executable}"
            )
            self.last_diagnostic_message = (
                f"Exécutable {executable} démarré pour le package {package}. "
                f"Logs : {log_path}."
            )
        except FileNotFoundError:
            self.last_diagnostic_message = (
                f"Impossible de lancer {executable} : commande introuvable."
            )
            self.get_logger().error(self.last_diagnostic_message)
        except Exception as exc:
            self.last_diagnostic_message = (
                f"Erreur lors du lancement de {package}/{executable} : {exc}"
            )
            self.get_logger().error(self.last_diagnostic_message)

    def stop_launch(
        self,
        package: Optional[str] = None,
        launch_file: Optional[str] = None,
    ) -> None:
        self._cleanup_finished_launches()

        if package and launch_file:
            keys = [self._launch_key(package, launch_file)]
        elif package:
            keys = [
                key for key in self.launch_processes
                if key.startswith(f"{package}/")
            ]
        elif launch_file:
            self.last_diagnostic_message = (
                "Arrêt de launch refusé : package manquant pour le launch_file demandé."
            )
            self.get_logger().warning(self.last_diagnostic_message)
            return
        else:
            keys = list(self.launch_processes)

        self._stop_processes(keys)

    def stop_executable(self, package: str, executable: str) -> None:
        self._cleanup_finished_launches()
        self._stop_processes([self._executable_key(package, executable)])

    def _stop_processes(self, keys: List[str]) -> None:
        stopped = []
        for key in keys:
            proc = self.launch_processes.pop(key, None)
            if proc is None:
                continue

            self.get_logger().info(f"Arrêt de la brique {key} pid={proc.pid}")
            try:
                os.killpg(proc.pid, signal.SIGINT)
                proc.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                self.get_logger().warning(
                    f"{key} ne répond pas à SIGINT, envoi de SIGTERM."
                )
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    self.get_logger().warning(
                        f"{key} ne répond pas à SIGTERM, envoi de SIGKILL."
                    )
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        pass
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
            stopped.append(key)

        if stopped:
            self.last_diagnostic_message = (
                f"Brique(s) arrêtée(s) : {', '.join(sorted(stopped))}."
            )
        else:
            self.last_diagnostic_message = "Aucune brique active ne correspond à la demande."
        self.get_logger().info(self.last_diagnostic_message)

    def shutdown_launch_processes(self) -> None:
        self.stop_launch()

    def _normalize_angle(self, angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def _sector_min_distance(
        self,
        distances: list[float],
        angles: list[float],
        center_angle: float,
        width: float,
    ) -> float:
        sector = [
            d
            for d, a in zip(distances, angles)
            if abs(self._normalize_angle(a - center_angle)) <= width / 2.0
        ]
        return min(sector) if sector else float("inf")

    def scan_callback(self, msg: LaserScan) -> None:
        distances = [r if math.isfinite(r) else msg.range_max or float("inf") for r in msg.ranges]
        if not distances:
            return

        angles = [msg.angle_min + i * msg.angle_increment for i in range(len(distances))]
        self.closest_obstacle_m = min(distances)

        self.front_distance_m = self._sector_min_distance(distances, angles, 0.0, math.radians(90))
        self.rear_distance_m = self._sector_min_distance(distances, angles, math.pi, math.radians(90))
        self.left_distance_m = self._sector_min_distance(distances, angles, math.radians(90), math.radians(90))
        self.right_distance_m = self._sector_min_distance(distances, angles, -math.radians(90), math.radians(90))

        if self.closest_obstacle_m <= self.obstacle_threshold_m:
            self.get_logger().warn(
                f"Obstacle détecté proche ({self.closest_obstacle_m:.2f} m)."
            )

        self.last_obstacle_report = (
            "Obstacle détecté proche : "
            f"avant={self.front_distance_m:.2f} m, "
            f"arrière={self.rear_distance_m:.2f} m, "
            f"droite={self.right_distance_m:.2f} m, "
            f"gauche={self.left_distance_m:.2f} m."
        )

    def get_obstacle_status(self) -> str:
        if self.closest_obstacle_m <= self.obstacle_threshold_m:
            return (
                f"Obstacle détecté à {self.closest_obstacle_m:.2f} m. "
                "Direction critique : "
                f"avant={self.front_distance_m:.2f} m, "
                f"arrière={self.rear_distance_m:.2f} m."
            )
        return (
            f"Aucun obstacle critique détecté. Distance la plus proche : "
            f"{self.closest_obstacle_m:.2f} m."
        )

    def _is_direction_blocked(self, linear_x: float, angular_z: float) -> bool:
        if linear_x > 0.0 and self.front_distance_m <= self.obstacle_threshold_m:
            return True
        if linear_x < 0.0 and self.rear_distance_m <= self.obstacle_threshold_m:
            return True
        if angular_z > 0.0 and self.left_distance_m <= self.obstacle_threshold_m:
            return True
        if angular_z < 0.0 and self.right_distance_m <= self.obstacle_threshold_m:
            return True
        return False

    def get_diagnostics(self) -> str:
        return (
            "Diagnostic continu : "
            f"Dernière action : {self.last_action_attempt}. "
            f"Dernier message : {self.last_diagnostic_message}. "
            f"{self.get_obstacle_status()}"
        )

    def get_execution_status(self) -> str:
        status = "en cours d'exécution" if self.is_executing else "au repos"
        return (
            "Statut d'exécution : "
            f"Le robot est {status}. "
            f"Dernière tentative d'action : {self.last_action_attempt}. "
            f"{self.get_launch_status()}"
        )

    def get_motion_status(self) -> str:
        motion = "en mouvement" if self.is_executing else "au repos"
        return (
            "Statut de mouvement : "
            f"Le robot est {motion}."
        )

    def publish_for_duration(
        self,
        linear_x: float = 0.0,
        angular_z: float = 0.0,
        duration: float = 0.0,
        target: str = "robot",
    ) -> None:
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z

        start_time = time.time()
        while time.time() - start_time < duration:
            if target == "robot" and self._is_direction_blocked(linear_x, angular_z):
                self.last_diagnostic_message = (
                    "Mouvement interrompu car l'obstacle bloque la direction demandée."
                )
                self.get_logger().warn(
                    "Publication interrompue : obstacle détecté dans la direction du mouvement."
                )
                break

            if target == "mannequin":
                self.actor_pub.publish(msg)
            else:
                self.cmd_pub.publish(msg)

            rclpy.spin_once(self, timeout_sec=0.05)
            time.sleep(0.05)

        self.stop(target=target)

    def execute_action(self, action: Dict) -> None:
        action_type = action["type"]
        target = action.get("target", "robot")
        self.last_action_attempt = f"{action_type} target={target}"

        if action_type == "move_forward":
            speed = 0.15
            duration = action["distance_m"] / speed
            self.publish_for_duration(linear_x=speed, duration=duration, target=target)

        elif action_type == "move_backward":
            speed = -0.15
            duration = action["distance_m"] / abs(speed)
            self.publish_for_duration(linear_x=speed, duration=duration, target=target)

        elif action_type == "turn_left":
            angular_speed = 0.5
            duration = math.radians(action["angle_deg"]) / angular_speed
            self.publish_for_duration(angular_z=angular_speed, duration=duration, target=target)

        elif action_type == "turn_right":
            angular_speed = -0.5
            duration = math.radians(action["angle_deg"]) / abs(angular_speed)
            self.publish_for_duration(angular_z=angular_speed, duration=duration, target=target)

        elif action_type == "wait":
            start_time = time.time()
            while time.time() - start_time < action["duration_s"]:
                rclpy.spin_once(self, timeout_sec=0.05)
                time.sleep(0.05)

        elif action_type == "launch_file":
            self.launch_file(
                package=action["package"],
                launch_file=action["launch_file"],
                arguments=action.get("arguments"),
            )

        elif action_type == "stop_launch":
            self.stop_launch(
                package=action.get("package"),
                launch_file=action.get("launch_file"),
            )

        elif action_type == "start_executable":
            self.start_executable(
                package=action["package"],
                executable=action["executable"],
                arguments=action.get("arguments"),
            )

        elif action_type == "stop_executable":
            self.stop_executable(
                package=action["package"],
                executable=action["executable"],
            )

        elif action_type == "stop":
            self.stop(target=target)

        else:
            self.get_logger().warning(f"Unknown action type: {action_type}")

    def execute_plan(self, actions: List[Dict]) -> None:
        self.is_executing = True
        try:
            for action in actions:
                #self.get_logger().info(f"Executing: {action}")
                self.execute_action(action)
        finally:
            self.is_executing = False


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
        node.shutdown_launch_processes()
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
