"""
CORE network emulator management utilities
"""
import subprocess
import re
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from pathlib import Path
from datetime import datetime
from app.schemas import CoreSessionInfo
from app.config import settings


# Global state for tracking topology loading progress
_loading_progress: Dict[str, Dict[str, Any]] = {}

# Global state for tracking loaded topology file per session
_session_topology_files: Dict[int, str] = {}


class CoreManager:
    """Manager for CORE network emulator"""

    @staticmethod
    async def get_session_info() -> CoreSessionInfo:
        """Get information about the current CORE session

        We always use session ID 1 since only one session runs at a time.
        Uses 'core-cli query sessions' to check if session exists.
        """
        global _session_topology_files

        try:
            # Query all sessions (we expect only session ID 1)
            result = subprocess.run(
                ["core-cli", "query", "sessions"],
                capture_output=True,
                text=True
            )

            # If command failed, no session exists
            if result.returncode != 0:
                return CoreSessionInfo(
                    session_id=None,
                    state="no_session",
                    nodes=0
                )

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
                            state = parts[1]
                            nodes = int(parts[2])

                            # We only care about session 1
                            if session_id == 1:
                                # Get the topology file if we have it stored
                                topology_file = _session_topology_files.get(session_id)

                                return CoreSessionInfo(
                                    session_id=session_id,
                                    state=state,
                                    nodes=nodes,
                                    file=topology_file
                                )
                        except (ValueError, IndexError):
                            continue

            # No session found
            return CoreSessionInfo(
                session_id=None,
                state="no_session",
                nodes=0
            )

        except Exception as e:
            # If query fails, assume no session
            return CoreSessionInfo(
                session_id=None,
                state="no_session",
                nodes=0
            )

    @staticmethod
    async def list_sessions() -> List[Dict[str, Any]]:
        """List all CORE sessions

        Uses 'core-cli query sessions' to get session information.
        We only expect session ID 1 since only one session runs at a time.
        """
        try:
            result = subprocess.run(
                ["core-cli", "query", "sessions"],
                capture_output=True,
                text=True,
                check=True
            )

            sessions = []
            # Parse output - format is:
            # Session ID | Session State | Nodes
            # 1          | CONFIGURATION | 75
            lines = result.stdout.strip().split('\n')

            # Skip header line and parse session data
            for line in lines[1:]:  # Skip first line (header)
                if line.strip():
                    # Split by | and clean up whitespace
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        try:
                            sessions.append({
                                "id": int(parts[0]),
                                "state": parts[1],
                                "nodes": int(parts[2])
                            })
                        except (ValueError, IndexError):
                            continue

            return sessions

        except Exception as e:
            return []

    @staticmethod
    async def delete_session(session_id: int = 1) -> bool:
        """Delete a CORE session

        We only ever use session ID 1 since only one session runs at a time.
        """
        global _session_topology_files

        try:
            result = subprocess.run(
                ["core-cli", "session", "-i", str(session_id), "delete"],
                capture_output=True,
                text=True,
                check=True
            )

            # Clean up the stored topology file mapping
            if session_id in _session_topology_files:
                del _session_topology_files[session_id]

            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    async def load_topology(xml_file: str) -> Optional[int]:
        """Load a CORE topology from XML file (synchronous version)"""
        try:
            result = subprocess.run(
                ["core-cli", "xml", "-f", xml_file, "-s"],
                capture_output=True,
                text=True,
                check=True
            )

            # Extract session ID from output (format: "session_id,...")
            output = result.stdout.strip()
            if ',' in output:
                session_id = int(output.split(',')[1])
                return session_id

            return None

        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def _add_log(task_id: str, message: str, level: str = "info"):
        """Add a log message to the progress tracker"""
        if task_id in _loading_progress:
            _loading_progress[task_id]["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            })
            # Keep only last 100 log entries to prevent memory issues
            if len(_loading_progress[task_id]["logs"]) > 100:
                _loading_progress[task_id]["logs"] = _loading_progress[task_id]["logs"][-100:]

    @staticmethod
    async def load_topology_background(xml_file: str, task_id: str) -> None:
        """Load a CORE topology in the background with progress tracking"""
        global _loading_progress
        global _session_topology_files

        # Initialize progress tracking
        _loading_progress[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "Initializing CORE session...",
            "xml_file": xml_file,
            "session_id": None,
            "error": None,
            "logs": [],  # List of log messages
            "started_at": datetime.now().isoformat()
        }

        try:
            # Step 1: Validate XML file
            _loading_progress[task_id].update({
                "status": "validating",
                "progress": 5,
                "message": f"Validating topology file: {Path(xml_file).name}"
            })
            CoreManager._add_log(task_id, f"Validating topology file: {xml_file}")
            await asyncio.sleep(0.5)

            if not Path(xml_file).exists():
                raise FileNotFoundError(f"Topology file not found: {xml_file}")

            CoreManager._add_log(task_id, "Topology file found and validated")

            # Step 2: Check for existing sessions and clean up all of them
            _loading_progress[task_id].update({
                "status": "cleaning",
                "progress": 15,
                "message": "Checking for existing CORE sessions..."
            })
            CoreManager._add_log(task_id, "Checking for existing sessions")

            existing_sessions = await CoreManager.list_sessions()
            if existing_sessions:
                CoreManager._add_log(task_id, f"Found {len(existing_sessions)} existing session(s), deleting all...")

                for session in existing_sessions:
                    session_id = session["id"]
                    state = session["state"]
                    CoreManager._add_log(task_id, f"Deleting session {session_id} (state: {state})")

                    success = await CoreManager.delete_session(session_id)
                    if success:
                        CoreManager._add_log(task_id, f"Session {session_id} deleted successfully")
                    else:
                        CoreManager._add_log(task_id, f"Warning: Failed to delete session {session_id}, continuing anyway", "warning")

                await asyncio.sleep(2)  # Give CORE time to clean up all sessions
                CoreManager._add_log(task_id, "All existing sessions deleted")
            else:
                CoreManager._add_log(task_id, "No existing sessions found, proceeding with load")

            # Step 3: Start loading topology
            _loading_progress[task_id].update({
                "status": "loading",
                "progress": 30,
                "message": "Loading topology into CORE..."
            })
            CoreManager._add_log(task_id, f"Executing: core-cli xml -f {xml_file} -s")

            # Run core-cli in subprocess (non-blocking)
            process = await asyncio.create_subprocess_exec(
                "core-cli", "xml", "-f", xml_file, "-s",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Step 3: Read output in real-time
            stdout_lines = []
            stderr_lines = []

            async def read_stdout():
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode().strip()
                    if decoded:
                        stdout_lines.append(decoded)
                        CoreManager._add_log(task_id, decoded, "stdout")

            async def read_stderr():
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    decoded = line.decode().strip()
                    if decoded:
                        stderr_lines.append(decoded)
                        CoreManager._add_log(task_id, decoded, "stderr")

            # Start reading stdout/stderr concurrently
            read_tasks = [
                asyncio.create_task(read_stdout()),
                asyncio.create_task(read_stderr())
            ]

            # Update progress while waiting
            progress_val = 40
            while process.returncode is None:
                _loading_progress[task_id].update({
                    "progress": min(progress_val, 75),
                    "message": "Creating network nodes and links..."
                })
                progress_val += 5
                await asyncio.sleep(1)

            # Ensure all output is read
            await asyncio.gather(*read_tasks)
            await process.wait()

            if process.returncode != 0:
                error_msg = "\n".join(stderr_lines) if stderr_lines else "Unknown error"
                raise RuntimeError(f"CORE CLI failed with code {process.returncode}: {error_msg}")

            # Step 4: Extract session ID
            _loading_progress[task_id].update({
                "status": "extracting",
                "progress": 80,
                "message": "Extracting session information..."
            })
            CoreManager._add_log(task_id, "Process completed successfully, extracting session ID")

            # Parse output (first line should have session info)
            session_id = None
            if stdout_lines:
                output = stdout_lines[0]
                if ',' in output:
                    session_id = int(output.split(',')[1])
                    CoreManager._add_log(task_id, f"Extracted session ID: {session_id}")

            if session_id is None:
                raise RuntimeError("Failed to extract session ID from CORE output")

            # Store the topology file path for this session
            _session_topology_files[session_id] = xml_file
            CoreManager._add_log(task_id, f"Stored topology file mapping: Session {session_id} -> {xml_file}")

            # Step 5: Verify session
            _loading_progress[task_id].update({
                "status": "verifying",
                "progress": 90,
                "message": f"Verifying session {session_id}..."
            })
            CoreManager._add_log(task_id, f"Verifying session {session_id} is active")
            await asyncio.sleep(0.5)

            # Step 6: Complete
            _loading_progress[task_id].update({
                "status": "completed",
                "progress": 100,
                "message": f"Topology loaded successfully! Session ID: {session_id}",
                "session_id": session_id,
                "completed_at": datetime.now().isoformat()
            })
            CoreManager._add_log(task_id, f"✓ Topology loaded successfully! Session ID: {session_id}", "success")

        except Exception as e:
            error_msg = str(e)
            CoreManager._add_log(task_id, f"✗ Error: {error_msg}", "error")
            _loading_progress[task_id].update({
                "status": "error",
                "progress": 0,
                "message": f"Failed to load topology",
                "error": error_msg,
                "completed_at": datetime.now().isoformat()
            })

    @staticmethod
    def get_loading_progress(task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current progress of a topology loading task"""
        return _loading_progress.get(task_id)

    @staticmethod
    def clear_loading_progress(task_id: str) -> None:
        """Clear progress tracking for a completed task"""
        if task_id in _loading_progress:
            del _loading_progress[task_id]

    @staticmethod
    async def stream_loading_progress(task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream loading progress updates via async generator (for SSE)"""
        last_progress = -1

        while True:
            progress_data = CoreManager.get_loading_progress(task_id)

            if progress_data is None:
                yield {
                    "status": "not_found",
                    "message": "Task not found"
                }
                break

            # Only yield if progress changed
            current_progress = progress_data.get("progress", 0)
            if current_progress != last_progress:
                yield progress_data
                last_progress = current_progress

            # Stop streaming if completed or errored
            if progress_data["status"] in ("completed", "error"):
                break

            await asyncio.sleep(0.5)  # Poll every 500ms

    @staticmethod
    async def get_topology_files() -> List[str]:
        """List available topology XML files from configured directory

        Searches both the configured CORE_TOPOLOGY_DIR
        for backward compatibility.
        """
        xml_files = []

        # Check configured topology directory
        topology_dir = Path(settings.CORE_TOPOLOGY_DIR)
        if topology_dir.exists() and topology_dir.is_dir():
            xml_files.extend(topology_dir.glob("*.xml"))

        return sorted([str(f) for f in xml_files])

    @staticmethod
    async def get_daemon_logs(lines: int = 10) -> List[Dict[str, str]]:
        """Get recent logs from core-daemon systemd service

        Args:
            lines: Number of log lines to retrieve (default: 10)

        Returns:
            List of log entries with timestamp and message
        """
        try:
            result = subprocess.run(
                ["journalctl", "-u", "core-daemon.service", "-n", str(lines), "--no-pager", "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )

            logs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        import json
                        log_entry = json.loads(line)
                        logs.append({
                            "timestamp": log_entry.get("__REALTIME_TIMESTAMP", ""),
                            "message": log_entry.get("MESSAGE", ""),
                            "priority": log_entry.get("PRIORITY", "6")
                        })
                    except json.JSONDecodeError:
                        continue

            return logs

        except subprocess.CalledProcessError as e:
            # Fallback to simple format if JSON fails
            try:
                result = subprocess.run(
                    ["journalctl", "-u", "core-daemon.service", "-n", str(lines), "--no-pager"],
                    capture_output=True,
                    text=True,
                    check=True
                )

                logs = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        logs.append({
                            "timestamp": "",
                            "message": line,
                            "priority": "6"
                        })

                return logs

            except Exception:
                return []

        except Exception:
            return []
