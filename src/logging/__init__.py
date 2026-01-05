"""
Structured logging and monitoring for the AI Agent Framework.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else "logs", exist_ok=True)


def setup_logger(name: str) -> logging.Logger:
    """
    Setup a logger with both file and console handlers.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


class MetricsCollector:
    """Collects and stores metrics for monitoring."""

    def __init__(self):
        self.metrics = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "agents_online": 0,
            "agents_offline": 0,
            "total_execution_time": 0.0,
            "avg_latency_ms": 0.0,
        }
        self.logger = setup_logger(__name__)

    def record_task_completed(self, execution_time: float):
        """Record a completed task."""
        self.metrics["tasks_completed"] += 1
        self.metrics["total_execution_time"] += execution_time
        self.metrics["avg_latency_ms"] = (
            self.metrics["total_execution_time"] / self.metrics["tasks_completed"]
        )
        self.logger.info(f"Task completed. Execution time: {execution_time:.2f}s")

    def record_task_failed(self, error: str):
        """Record a failed task."""
        self.metrics["tasks_failed"] += 1
        self.logger.error(f"Task failed: {error}")

    def record_task_submitted(self):
        """Record a submitted task."""
        self.metrics["tasks_submitted"] += 1
        self.logger.info("Task submitted to queue.")

    def record_agent_online(self, agent_id: str):
        """Record agent coming online."""
        self.metrics["agents_online"] += 1
        self.logger.info(f"Agent {agent_id} is online.")

    def record_agent_offline(self, agent_id: str):
        """Record agent going offline."""
        self.metrics["agents_offline"] += 1
        self.logger.warning(f"Agent {agent_id} went offline.")

    def get_metrics(self):
        """Get current metrics."""
        return {
            **self.metrics,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global metrics instance
metrics_collector = MetricsCollector()
