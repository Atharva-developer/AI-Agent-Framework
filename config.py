"""
Centralized configuration for the AI Agent Framework.
Settings can be overridden by environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
KAFKA_API_VERSION = tuple(map(int, os.getenv("KAFKA_API_VERSION", "0,10,1").split(",")))
KAFKA_PENDING_TOPIC = os.getenv("KAFKA_PENDING_TOPIC", "pending_tasks")
KAFKA_COMPLETED_TOPIC = os.getenv("KAFKA_COMPLETED_TOPIC", "completed_tasks")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "agent_group_1")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_framework.db")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "False").lower() == "true"

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"
API_WORKERS = int(os.getenv("API_WORKERS", "4"))

# Security Configuration
API_KEY_ENABLED = os.getenv("API_KEY_ENABLED", "True").lower() == "true"
API_KEYS = os.getenv("API_KEYS", "default-key-change-me").split(",")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/agent_framework.log")

# Agent Configuration
DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
ENABLE_INTEL_OPTIMIZATION = os.getenv("ENABLE_INTEL_OPTIMIZATION", "False").lower() == "true"
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "100"))

# Load Balancer Configuration
LOAD_BALANCER_STRATEGY = os.getenv("LOAD_BALANCER_STRATEGY", "round_robin")  # round_robin, least_busy, random
AGENT_HEALTH_CHECK_INTERVAL = int(os.getenv("AGENT_HEALTH_CHECK_INTERVAL", "30"))

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "2"))

# Monitoring
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "True").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))
