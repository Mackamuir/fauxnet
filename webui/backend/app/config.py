"""
Configuration settings for Fauxnet Web UI
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Fauxnet Management Interface"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "fauxnet"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fauxnet.db"

    # CORS - Allow all origins for development
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    # Fauxnet Paths
    FAUXNET_CERTS: str = "/opt/fauxnet/certs"

    # CORE Network Emulator Paths
    CORE_TOPOLOGY_DIR: str = "/opt/fauxnet/topologies"  # Directory containing CORE XML topology files
    CORE_SESSION_FILE: Optional[str] = None  # Optional: Path to file storing active session ID (e.g., /run/core-session.sid)

    # Service Management
    CORE_DAEMON_PORT: int = 50051

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string from .env
            if v.strip() == '':
                return ["http://localhost:3000", "http://localhost:8080"]
            return [origin.strip() for origin in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()