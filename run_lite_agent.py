"""
Entry point to start a lite agent (no heavy model).
"""

from src.agents.lite_agent import LiteAgent
from src.logging import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    agent = LiteAgent(name="LiteWorker-1")
    agent.start_listening()
