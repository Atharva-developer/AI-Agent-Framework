"""
Database models for the AI Agent Framework.
Stores task history, results, agent metrics, and users.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum, ForeignKey, create_engine, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

Base = declarative_base()


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    RETRYING = "retrying"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TaskModel(Base):
    """Stores all tasks submitted to the framework."""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.NORMAL, index=True)
    assigned_agent = Column(String, nullable=True, index=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    workflow_id = Column(String, nullable=True, index=True)
    batch_id = Column(String, nullable=True, index=True)
    
    # Scheduling & retry fields
    scheduled_time = Column(DateTime, nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_time = Column(DateTime, nullable=True)
    
    # Dependencies
    depends_on = Column(String, nullable=True)  # comma-separated task IDs
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time = Column(Float, nullable=True)  # seconds

    # Relationships
    metrics = relationship("TaskMetricModel", back_populates="task", cascade="all, delete-orphan")


class TaskMetricModel(Base):
    """Stores metrics for each task execution."""
    __tablename__ = "task_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_id = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    task = relationship("TaskModel", back_populates="metrics")


class AgentModel(Base):
    """Stores agent registration and health status."""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    model_id = Column(String, nullable=True)
    status = Column(String, default="offline", index=True)  # online, offline, busy
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserModel(Base):
    """Stores user information for API authentication."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    api_key = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(String, default="active")  # active, inactive
    permissions = Column(String, default="read,submit")  # comma-separated permissions
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)


class WorkflowModel(Base):
    """Stores workflow definitions and execution history."""
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(Text, nullable=False)  # JSON serialized list of steps
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
