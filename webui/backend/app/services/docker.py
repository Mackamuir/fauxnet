"""
Docker service management utilities
"""
import docker
from typing import List, Dict, Any
from pathlib import Path


class DockerManager:
    """Manager for Docker and Docker Compose services"""

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            self.client = None

    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Get status of a Docker container"""
        if not self.client:
            return {"error": "Docker client not available"}

        try:
            container = self.client.containers.get(container_name)
            return {
                "name": container.name,
                "status": container.status,
                "state": container.attrs["State"],
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "ports": container.ports
            }
        except docker.errors.NotFound:
            return {"error": f"Container {container_name} not found"}
        except Exception as e:
            return {"error": str(e)}

    def list_containers(self, all: bool = False) -> List[Dict[str, Any]]:
        """List all Docker containers"""
        if not self.client:
            return []

        try:
            containers = self.client.containers.list(all=all)
            return [
                {
                    "id": c.short_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "ports": c.ports
                }
                for c in containers
            ]
        except Exception as e:
            return []

    def start_container(self, container_name: str) -> bool:
        """Start a Docker container"""
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_name)
            container.start()
            return True
        except Exception as e:
            return False

    def stop_container(self, container_name: str) -> bool:
        """Stop a Docker container"""
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_name)
            container.stop()
            return True
        except Exception as e:
            return False

    def restart_container(self, container_name: str) -> bool:
        """Restart a Docker container"""
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_name)
            container.restart()
            return True
        except Exception as e:
            return False

    def get_container_logs(self, container_name: str, lines: int = 100) -> List[str]:
        """Get logs from a Docker container"""
        if not self.client:
            return []

        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs.split('\n')
        except Exception as e:
            return []
