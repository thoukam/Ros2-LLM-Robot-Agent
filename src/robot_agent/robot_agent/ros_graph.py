from __future__ import annotations

import os
from typing import Any, Dict, List

import tf2_ros
from rcl_interfaces.msg import Log
from rclpy.node import Node
from rclpy.time import Time


class ROSGraphInspector:
    def __init__(self, node: Node) -> None:
        self.node = node
        self.robot_control_topic = "/cmd_vel"
        self.mannequin_control_topic = "/actor/cmd_vel"
        self.log_history: List[Dict[str, Any]] = []
        self.log_sub = self.node.create_subscription(Log, "/rosout", self._rosout_callback, 10)
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self.node)
        self._common_tf_checks = [
            ("map", "base_link"),
            ("odom", "base_link"),
            ("map", "odom"),
            ("map", "base_footprint"),
        ]

    def discover_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for name, namespace in sorted(self.node.get_node_names_and_namespaces()):
            nodes.append({"name": name, "namespace": namespace})
        return nodes

    def discover_topics(self) -> List[Dict[str, Any]]:
        topics = []
        for name, types in sorted(self.node.get_topic_names_and_types()):
            topics.append({"name": name, "types": sorted(types)})
        return topics

    def discover_services(self) -> List[Dict[str, Any]]:
        services = []
        for name, types in sorted(self.node.get_service_names_and_types()):
            services.append({"name": name, "types": sorted(types)})
        return services

    def discover_endpoints(self) -> Dict[str, Any]:
        endpoints = {"nodes": []}
        for node_info in self.discover_nodes():
            node_name = node_info["name"]
            node_namespace = node_info["namespace"]
            publishers = self.node.get_publisher_names_and_types_by_node(node_name, node_namespace)
            subscribers = self.node.get_subscriber_names_and_types_by_node(node_name, node_namespace)
            services = self.node.get_service_names_and_types_by_node(node_name, node_namespace)

            endpoints["nodes"].append(
                {
                    "name": node_name,
                    "namespace": node_namespace,
                    "publishers": [
                        {"topic": topic, "types": sorted(types)} for topic, types in sorted(publishers)
                    ],
                    "subscribers": [
                        {"topic": topic, "types": sorted(types)} for topic, types in sorted(subscribers)
                    ],
                    "services": [
                        {"service": service, "types": sorted(types)} for service, types in sorted(services)
                    ],
                }
            )

        return endpoints

    def _topic_status(self, topic_name: str, endpoints: Dict[str, Any]) -> str:
        publishers = []
        subscribers = []
        for node_info in endpoints["nodes"]:
            for publisher in node_info["publishers"]:
                if publisher["topic"] == topic_name:
                    publishers.append(node_info["name"])
            for subscriber in node_info["subscribers"]:
                if subscriber["topic"] == topic_name:
                    subscribers.append(node_info["name"])

        if publishers and subscribers:
            return (
                f"Topic {topic_name} publié par {', '.join(sorted(set(publishers)))} "
                f"et abonné par {', '.join(sorted(set(subscribers)))}. Entité prête à recevoir des commandes."
            )
        if publishers and not subscribers:
            return (
                f"Topic {topic_name} publié par {', '.join(sorted(set(publishers)))} "
                "mais sans abonné actif. Entité non prête à recevoir des commandes."
            )
        if not publishers and subscribers:
            return (
                f"Topic {topic_name} a des abonnés ({', '.join(sorted(set(subscribers)))}) "
                "mais aucun éditeur actuel. État non prêt."
            )
        return f"Topic {topic_name} absent du graph ROS2. Entité hors ligne."

    def _transform_age(self, transform) -> float:
        stamp = transform.header.stamp
        stamp_time = Time(seconds=float(stamp.sec), nanoseconds=int(stamp.nanosec))
        age_s = (self.node.get_clock().now().nanoseconds - stamp_time.nanoseconds) * 1e-9
        return max(age_s, 0.0)

    def _check_common_transforms(self) -> List[str]:
        problems = []
        for target, source in self._common_tf_checks:
            try:
                if not self._tf_buffer.can_transform(target, source, Time()):
                    problems.append(f"Transform manquant ou incomplet : {source} -> {target}")
                    continue
                transform = self._tf_buffer.lookup_transform(target, source, Time())
                age = self._transform_age(transform)
                if age > 0.5:
                    problems.append(
                        f"Transform {source} -> {target} existe, mais en retard ({age:.2f}s)"
                    )
            except Exception as exc:
                problems.append(f"Impossible de vérifier transform {source} -> {target} : {exc}")
        return problems

    def summarize_tf(self) -> str:
        try:
            frames_yaml = self._tf_buffer.all_frames_as_yaml()
        except Exception:
            frames_yaml = ""

        if not frames_yaml:
            return "Aucun transform /tf reçu ou buffer TF vide."

        problems = self._check_common_transforms()
        summary = [
            "Etat des transforms /tf :",
            "Transformations captées :",
            frames_yaml.strip(),
        ]
        if problems:
            summary.append("Problèmes TF détectés :")
            summary.extend(problems)
        else:
            summary.append("Aucun problème TF critique détecté sur les transformées courantes.")
        return "\n".join(summary)

    def _rosout_callback(self, msg: Log) -> None:
        self.log_history.append(
            {"name": msg.name, "level": msg.level, "message": msg.msg}
        )
        if len(self.log_history) > 100:
            self.log_history.pop(0)

    def _infer_algorithms_from_graph(self) -> str:
        endpoints = self.discover_endpoints()
        algorithm_keywords = {
            "navigation": [
                "nav2",
                "bt_navigator",
                "planner_server",
                "controller_server",
                "dwb",
                "navigate_to_pose",
                "move_base",
            ],
            "slam": [
                "slam",
                "amcl",
                "map_server",
                "scan_matcher",
                "slam_toolbox",
                "cartographer",
            ],
            "exploration": [
                "explorer",
                "frontier",
                "exploration",
                "frontier_exploration",
            ],
        }

        active_algos = set()
        for node_info in endpoints["nodes"]:
            node_name = node_info["name"].lower()
            for algo, keys in algorithm_keywords.items():
                if any(key in node_name for key in keys):
                    active_algos.add(algo)
            for publisher in node_info["publishers"]:
                topic_name = publisher["topic"].lower()
                for algo, keys in algorithm_keywords.items():
                    if any(key in topic_name for key in keys):
                        active_algos.add(algo)
            for subscriber in node_info["subscribers"]:
                topic_name = subscriber["topic"].lower()
                for algo, keys in algorithm_keywords.items():
                    if any(key in topic_name for key in keys):
                        active_algos.add(algo)

        if active_algos:
            return "Algorithmes probables détectés par le graph : " + ", ".join(sorted(active_algos)) + "."
        return "Aucun composant de navigation, SLAM ou exploration clairement détecté dans le graph ROS2."

    def _extract_algorithm_status(self) -> str:
        if not self.log_history:
            return "Aucun message /rosout récent."

        active_keywords = {
            "navigation": [
                "goal accepted",
                "goal active",
                "path planning",
                "planner",
                "move_base",
                "followed goal",
                "recovery",
                "controller",
                "navigating",
                "approaching goal",
                "reached goal",
            ],
            "slam": [
                "map_update",
                "map_build",
                "localization",
                "amcl",
                "scan_matcher",
                "pose estimate",
                "pose update",
                "laser_scan",
            ],
            "exploration": [
                "frontier",
                "explorer",
                "exploration",
                "searching frontiers",
                "explore",
            ],
        }

        presence_keywords = {
            "navigation": [
                "nav2",
                "navigate",
                "planner_server",
                "controller_server",
                "dwb",
                "navigate_to_pose",
                "move_base",
                "route_server",
            ],
            "slam": [
                "slam",
                "amcl",
                "map_server",
                "scan_matcher",
                "slam_toolbox",
                "cartographer",
            ],
            "exploration": [
                "explorer",
                "frontier_exploration",
                "frontier",
                "exploration",
            ],
        }

        active_algos = set()
        present_algos = set()
        for entry in self.log_history[-50:]:
            text = f"{entry['name']}: {entry['message']}".lower()
            for algo, keys in presence_keywords.items():
                if any(key in text for key in keys):
                    present_algos.add(algo)
            for algo, keys in active_keywords.items():
                if any(key in text for key in keys):
                    active_algos.add(algo)

        idle_algos = present_algos - active_algos
        lines: List[str] = []
        if active_algos:
            lines.append("Algorithmes actifs détectés dans /rosout : " + ", ".join(sorted(active_algos)) + ".")
        if idle_algos:
            lines.append(
                "Algorithmes chargés ou présents mais sans activité récente détectée : "
                + ", ".join(sorted(idle_algos))
                + "."
            )
        if not lines:
            return "Aucun algorithme de navigation, SLAM ou exploration actif ni clairement présent dans /rosout."
        return " ".join(lines)

    def summarize_rosout(self) -> str:
        graph_inference = self._infer_algorithms_from_graph()
        if not self.log_history:
            return (
                "Aucun message /rosout reçu. "
                f"{graph_inference}"
            )

        last = self.log_history[-1]
        return (
            f"Dernier log /rosout : {last['name']} - {last['message']} (niveau {last['level']}). "
            f"{self._extract_algorithm_status()} {graph_inference}"
        )

    def detect_robot_availability(self, topics: List[Dict[str, Any]], endpoints: Dict[str, Any]) -> str:
        robot_status = self._topic_status(self.robot_control_topic, endpoints)
        mannequin_status = self._topic_status(self.mannequin_control_topic, endpoints)
        return (
            f"État robot: {robot_status} "
            f"État mannequin: {mannequin_status}"
        )

    def summarize_graph(self) -> str:
        nodes = self.discover_nodes()
        topics = self.discover_topics()
        services = self.discover_services()
        endpoints = self.discover_endpoints()

        lines: List[str] = []
        lines.append("Résumé du graph ROS2 :")
        lines.append(self.detect_robot_availability(topics, endpoints))
        lines.append(f"- {len(nodes)} noeud(s)")
        lines.append(f"- {len(topics)} topic(s)")
        lines.append(f"- {len(services)} service(s)")
        lines.append("")

        for node_info in endpoints["nodes"]:
            full_name = f"{node_info['namespace']}/{node_info['name']}".replace("//", "/")
            lines.append(f"Noeud: {full_name}")
            if node_info["publishers"]:
                lines.append("  Publishers:")
                for publisher in node_info["publishers"]:
                    lines.append(f"    - {publisher['topic']} ({', '.join(publisher['types'])})")
            else:
                lines.append("  Publishers: aucun")

            if node_info["subscribers"]:
                lines.append("  Subscribers:")
                for subscriber in node_info["subscribers"]:
                    lines.append(f"    - {subscriber['topic']} ({', '.join(subscriber['types'])})")
            else:
                lines.append("  Subscribers: aucun")

            if node_info["services"]:
                lines.append("  Services:")
                for service in node_info["services"]:
                    lines.append(f"    - {service['service']} ({', '.join(service['types'])})")
            else:
                lines.append("  Services: aucun")

            lines.append("")

        lines.append("Liste des topics connus :")
        for topic in topics:
            lines.append(f"- {topic['name']} ({', '.join(topic['types'])})")

        if services:
            lines.append("")
            lines.append("Liste des services connus :")
            for service in services:
                lines.append(f"- {service['name']} ({', '.join(service['types'])})")

        return "\n".join(lines)
