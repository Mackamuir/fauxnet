"""
Progress tracking for long-running operations
"""
import asyncio
import uuid
from typing import Dict, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track progress for long-running operations"""

    def __init__(self, operation_id: str, total_phases: int = 7):
        self.operation_id = operation_id
        self.total_phases = total_phases
        self.current_phase = 0
        self.current_phase_name = ""
        self.current_phase_progress = 0
        self.current_phase_total = 0
        self.status = "running"  # running, completed, error
        self.error = None
        self.started_at = datetime.now()
        self.completed_at = None
        self.messages = []

    def update(self, phase: int, phase_name: str, progress: int = 0, total: int = 0, message: str = ""):
        """Update progress"""
        self.current_phase = phase
        self.current_phase_name = phase_name
        self.current_phase_progress = progress
        self.current_phase_total = total
        if message:
            self.messages.append({
                "timestamp": datetime.now().isoformat(),
                "message": message
            })
            logger.info(f"[{self.operation_id}] {message}")

    def complete(self):
        """Mark operation as completed"""
        self.status = "completed"
        self.completed_at = datetime.now()

    def error_occurred(self, error: str):
        """Mark operation as failed"""
        self.status = "error"
        self.error = error
        self.completed_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "current_phase": self.current_phase,
            "total_phases": self.total_phases,
            "current_phase_name": self.current_phase_name,
            "current_phase_progress": self.current_phase_progress,
            "current_phase_total": self.current_phase_total,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "messages": self.messages[-10:]  # Last 10 messages
        }


class ProgressManager:
    """Manage multiple progress trackers"""

    _instance = None
    _trackers: Dict[str, ProgressTracker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._trackers = {}
        return cls._instance

    @classmethod
    def create_tracker(cls, total_phases: int = 7) -> ProgressTracker:
        """Create a new progress tracker"""
        operation_id = str(uuid.uuid4())
        tracker = ProgressTracker(operation_id, total_phases)
        cls._trackers[operation_id] = tracker
        return tracker

    @classmethod
    def get_tracker(cls, operation_id: str) -> Optional[ProgressTracker]:
        """Get a progress tracker by ID"""
        return cls._trackers.get(operation_id)

    @classmethod
    def remove_tracker(cls, operation_id: str):
        """Remove a progress tracker"""
        if operation_id in cls._trackers:
            del cls._trackers[operation_id]

    @classmethod
    def cleanup_old_trackers(cls, max_age_seconds: int = 3600):
        """Remove trackers older than max_age_seconds"""
        now = datetime.now()
        to_remove = []
        for operation_id, tracker in cls._trackers.items():
            if tracker.status in ["completed", "error"] and tracker.completed_at:
                age = (now - tracker.completed_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(operation_id)

        for operation_id in to_remove:
            del cls._trackers[operation_id]
