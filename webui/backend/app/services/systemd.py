"""
Systemd service management utilities
"""
import subprocess
import re
from typing import Dict, List
from app.schemas import ServiceStatus


class SystemdManager:
    """Manager for systemd services"""

    @staticmethod
    async def get_service_status(service_name: str) -> ServiceStatus:
        """Get the status of a systemd service"""
        try:
            # Get service status
            result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True,
                text=True
            )

            # Parse output
            status_output = result.stdout

            # Check if service is active
            is_active = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True
            ).stdout.strip()

            # Check if service is enabled
            is_enabled = subprocess.run(
                ["systemctl", "is-enabled", service_name],
                capture_output=True,
                text=True
            ).stdout.strip()

            # Extract PID if running
            pid = None
            pid_match = re.search(r"Main PID: (\d+)", status_output)
            if pid_match:
                pid = int(pid_match.group(1))

            # Extract uptime if running
            uptime = None
            uptime_match = re.search(r"Active: active .* since (.+?);", status_output)
            if uptime_match:
                uptime = uptime_match.group(1)

            return ServiceStatus(
                name=service_name,
                status=is_active,
                active=(is_active == "active"),
                enabled=(is_enabled == "enabled"),
                uptime=uptime,
                pid=pid
            )

        except Exception as e:
            return ServiceStatus(
                name=service_name,
                status="error",
                active=False,
                enabled=False
            )

    @staticmethod
    async def start_service(service_name: str) -> bool:
        """Start a systemd service"""
        try:
            result = subprocess.run(
                ["systemctl", "start", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def stop_service(service_name: str) -> bool:
        """Stop a systemd service"""
        try:
            result = subprocess.run(
                ["systemctl", "stop", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def restart_service(service_name: str) -> bool:
        """Restart a systemd service"""
        try:
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def enable_service(service_name: str) -> bool:
        """Enable a systemd service"""
        try:
            result = subprocess.run(
                ["systemctl", "enable", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def disable_service(service_name: str) -> bool:
        """Disable a systemd service"""
        try:
            result = subprocess.run(
                ["systemctl", "disable", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def get_service_logs(service_name: str, lines: int = 100) -> List[str]:
        """Get logs for a systemd service"""
        try:
            result = subprocess.run(
                ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.split("\n")
        except subprocess.CalledProcessError:
            return []
