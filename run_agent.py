"""
Entry point to start a full-featured agent.
"""

from src.agents.base_agents import Agent
from src.logging import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    agent = Agent(
        name="IntelWorker-1",
        role="You are a helpful AI assistant."
    )
    agent.start_listening()
