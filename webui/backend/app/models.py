"""
Database models for Fauxnet Web UI
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from datetime import datetime
from app.database import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class VirtualHost(Base):
    """Virtual host configuration and metadata"""
    __tablename__ = "vhosts"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    ip_address = Column(String, nullable=True)
    status = Column(String, default="active")  # active, disabled, error
    scrape_url = Column(String, nullable=True)
    last_scraped = Column(DateTime, nullable=True)
    has_ssl = Column(Boolean, default=False)
    has_nginx_config = Column(Boolean, default=False)
    is_custom = Column(Boolean, default=False)
    extra_data = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ServiceLog(Base):
    """Service management logs"""
    __tablename__ = "service_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)  # start, stop, restart, status
    status = Column(String, nullable=False)  # success, failed
    message = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Configuration(Base):
    """System configuration key-value store"""
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
