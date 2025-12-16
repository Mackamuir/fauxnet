"""
Community service management utilities for CORE nodes
"""
import subprocess
import re
import yaml
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from pathlib import Path
from app.schemas import (
    CommunityServiceStatus,
    CommunityNodeStatus,
    CommunityConfig
)
from app.config import settings
from app.services.core import _session_topology_files


class CommunityManager:
    """Manager for Community service running in CORE nodes"""

    @staticmethod
    async def get_session_id() -> Optional[int]:
        """Get the current CORE session ID

        We always use session ID 1 since only one session runs at a time.
        Uses 'core-cli query sessions' to check if session exists.
        """
        try:
            # Query all sessions (we expect only session ID 1)
            result = subprocess.run(
                ["core-cli", "query", "sessions"],
                capture_output=True,
                text=True
            )

            # If command failed, no session exists
            if result.returncode != 0:
                return None

            # Parse output - format is:
            # Session ID | Session State | Nodes
            # 1          | CONFIGURATION | 75
            lines = result.stdout.strip().split('\n')

            # Skip header line and look for session data
            for line in lines[1:]:  # Skip first line (header)
                if line.strip():
                    # Split by | and clean up whitespace
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try:
                            session_id = int(parts[0])
                            # We only care about session 1
                            if session_id == 1:
                                return session_id
                        except (ValueError, IndexError):
                            continue

            # No session found
            return None

        except Exception:
            # If query fails, assume no session
            return None

    @staticmethod
    async def get_community_nodes_from_xml(xml_file: str = None) -> List[Dict[str, Any]]:
        """Get list of nodes with Community service from topology XML file

        Args:
            xml_file: Path to XML file. If None, uses the currently loaded topology file
        """
        if xml_file is None:
            # Get the currently loaded topology file from the active session
            session_id = await CommunityManager.get_session_id()
            if session_id and session_id in _session_topology_files:
                xml_file = _session_topology_files[session_id]

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            nodes = []
            # Find all device elements with Community service
            for device in root.findall('.//device'):
                services = device.find('services')
                if services is not None:
                    # Check if Community service exists
                    for service in services.findall('service'):
                        if service.get('name') == 'Community':
                            node_id = device.get('id')
                            node_name = device.get('name')
                            nodes.append({
                                "id": node_id,
                                "name": node_name
                            })
                            break

            return nodes

        except Exception as e:
            print(f"Error parsing XML for community nodes: {e}")
            return []

    @staticmethod
    async def get_community_nodes() -> List[Dict[str, Any]]:
        """Get list of nodes running the Community service

        This uses the XML topology file to identify which nodes have the Community service.
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return []

        # Get nodes from XML topology
        return await CommunityManager.get_community_nodes_from_xml()

    @staticmethod
    def _get_node_channel(session_id: int, node_name: str) -> Optional[str]:
        """Get the control channel path for a node

        Args:
            session_id: CORE session ID
            node_name: Node name (e.g., 'n14')

        Returns:
            Path to control channel socket or None if not found
        """
        try:
            channel_path = f"/tmp/pycore.{session_id}/{node_name}"
            if Path(channel_path).exists():
                return channel_path
            return None
        except Exception:
            return None

    @staticmethod
    async def get_node_status(session_id: int, node_id: str, node_name: str) -> CommunityNodeStatus:
        """Get status of Community service on a specific node"""
        try:
            # Get control channel for this node
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                return CommunityNodeStatus(
                    node_id=node_id,
                    node_name=node_name,
                    is_running=False,
                    config_path=f"/tmp/pycore.{session_id}/{node_name}.conf/opt.fauxnet.core.community/config.yaml",
                    error="Node control channel not found"
                )

            # Check if process is running
            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "pgrep", "-f", "/usr/bin/python3 /opt/fauxnet/core/community/community.py"],
                capture_output=True,
                text=True,
                timeout=5
            )

            is_running = result.returncode == 0
            pid = None
            uptime = None

            if is_running and result.stdout.strip():
                pid = int(result.stdout.strip().split('\n')[0])

                # Get process uptime
                uptime_result = subprocess.run(
                    ["vcmd", "-c", channel, "--", "ps", "-o", "etime=", "-p", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if uptime_result.returncode == 0:
                    uptime = uptime_result.stdout.strip()

            return CommunityNodeStatus(
                node_id=node_id,
                node_name=node_name,
                is_running=is_running,
                pid=pid,
                uptime=uptime,
                config_path=f"/tmp/pycore.{session_id}/{node_name}.conf/opt.fauxnet.core.community/config.yaml",
                log_path=f"/tmp/pycore.{session_id}/{node_name}.conf/community.log",
            )

        except Exception as e:
            print(f"Error getting node status: {e}")
            return CommunityNodeStatus(
                node_id=node_id,
                node_name=node_name,
                is_running=False,
                config_path=f"/tmp/pycore.{session_id}/{node_name}.conf/opt.fauxnet.core.community/config.yaml",
                error=str(e)
            )

    @staticmethod
    async def get_service_status() -> CommunityServiceStatus:
        """Get overall Community service status across all nodes"""
        session_id = await CommunityManager.get_session_id()

        if not session_id:
            return CommunityServiceStatus(
                session_active=False,
                nodes=[],
                total_nodes=0,
                running_nodes=0
            )

        nodes_info = await CommunityManager.get_community_nodes()
        node_statuses = []

        for node in nodes_info:
            status = await CommunityManager.get_node_status(
                session_id, node["id"], node["name"]
            )
            node_statuses.append(status)

        running_count = sum(1 for node in node_statuses if node.is_running)

        return CommunityServiceStatus(
            session_active=True,
            nodes=node_statuses,
            total_nodes=len(node_statuses),
            running_nodes=running_count
        )

    @staticmethod
    async def start_service(node_id: str, node_name: str) -> bool:
        """Start Community service on a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return False

        try:
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                print(f"Cannot find control channel for node {node_name}")
                return False

            # Start the service using the same command as in CORE service definition
            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "sh", "-c",
                 "PYTHONUNBUFFERED=1 /usr/bin/python3 /opt/fauxnet/core/community/community.py > ./community.log 2>&1 &"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error starting service: {e}")
            return False

    @staticmethod
    async def stop_service(node_id: str, node_name: str) -> bool:
        """Stop Community service on a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return False

        try:
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                print(f"Cannot find control channel for node {node_name}")
                return False

            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "pkill", "-f", "/usr/bin/python3 /opt/fauxnet/core/community/community.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return True  # pkill returns 0 if processes were killed, non-zero if none found
        except Exception as e:
            print(f"Error stopping service: {e}")
            return False

    @staticmethod
    async def restart_service(node_id: str, node_name: str) -> bool:
        """Restart Community service on a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
        """
        stop_success = await CommunityManager.stop_service(node_id, node_name)
        if not stop_success:
            return False

        # Wait a moment for the process to fully stop
        import asyncio
        await asyncio.sleep(1)

        return await CommunityManager.start_service(node_id, node_name)

    @staticmethod
    async def get_config(node_id: str, node_name: str) -> Optional[CommunityConfig]:
        """Get Community configuration from a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return None

        try:
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                return None

            # Read config file from node
            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "cat", "/opt/fauxnet/core/community/config.yaml"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                config_data = yaml.safe_load(result.stdout)
                return CommunityConfig(**config_data)

            return None

        except Exception as e:
            print(f"Error getting config: {e}")
            return None

    @staticmethod
    async def update_config(node_id: str, node_name: str, config: CommunityConfig) -> bool:
        """Update Community configuration on a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
            config: New configuration
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return False

        try:
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                return False

            # Convert config to YAML
            config_yaml = yaml.dump(config.dict(), default_flow_style=False)

            # Write config to node using echo
            escaped_yaml = config_yaml.replace("'", "'\\''")

            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "sh", "-c",
                 f"echo '{escaped_yaml}' > /opt/fauxnet/core/community/config.yaml"],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Error updating config: {e}")
            return False

    @staticmethod
    async def get_logs(node_id: str, node_name: str, lines: int = 100) -> List[str]:
        """Get logs from Community service on a specific node

        Args:
            node_id: Node ID
            node_name: Node name (used to find control channel)
            lines: Number of log lines to retrieve
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return []

        try:
            channel = CommunityManager._get_node_channel(session_id, node_name)
            if not channel:
                return []

            result = subprocess.run(
                ["vcmd", "-c", channel, "--", "sh", "-c",
                 f"tail -n {lines} ./community.log 2>/dev/null || echo 'Log file not found'"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.split('\n')

            return []

        except Exception as e:
            print(f"Error getting logs: {e}")
            return []

    @staticmethod
    async def get_base_config() -> Optional[CommunityConfig]:
        """Get base Community configuration from /opt/fauxnet/core/community/config.yaml

        This is the template config that nodes use. Can be read without nodes being online.
        """
        try:
            config_path = Path("/opt/fauxnet/core/community/config.yaml")
            if not config_path.exists():
                return None

            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            return CommunityConfig(**config_data)

        except Exception as e:
            print(f"Error getting base config: {e}")
            return None

    @staticmethod
    async def update_base_config(config: CommunityConfig) -> bool:
        """Update base Community configuration at /opt/fauxnet/core/community/config.yaml

        This updates the template config. Does not require nodes to be online.

        Args:
            config: New configuration
        """
        try:
            config_path = Path("/opt/fauxnet/core/community/config.yaml")

            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert config to YAML
            config_yaml = yaml.dump(config.dict(), default_flow_style=False)

            # Write to file
            with open(config_path, 'w') as f:
                f.write(config_yaml)

            return True

        except Exception as e:
            print(f"Error updating base config: {e}")
            return False

    @staticmethod
    async def update_all_nodes_config(config: CommunityConfig) -> Dict[str, Any]:
        """Update configuration on all Community nodes at once

        Args:
            config: New configuration to apply to all nodes

        Returns:
            Dict with success status and per-node results
        """
        session_id = await CommunityManager.get_session_id()
        if not session_id:
            return {
                "success": False,
                "message": "No active CORE session found",
                "results": []
            }

        # Get all community nodes
        nodes = await CommunityManager.get_community_nodes()
        if not nodes:
            return {
                "success": False,
                "message": "No Community nodes found",
                "results": []
            }

        results = []
        success_count = 0
        fail_count = 0

        # Update each node
        for node in nodes:
            node_id = node["id"]
            node_name = node["name"]

            success = await CommunityManager.update_config(node_id, node_name, config)

            results.append({
                "node_id": node_id,
                "node_name": node_name,
                "success": success
            })

            if success:
                success_count += 1
            else:
                fail_count += 1

        return {
            "success": fail_count == 0,
            "message": f"Updated {success_count}/{len(nodes)} nodes successfully",
            "total_nodes": len(nodes),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }
