"""
Load balancer for distributing tasks among agents.
Supports round-robin, least-busy, and random strategies.
"""

import random
from typing import List, Optional
from datetime import datetime, timedelta
from config import LOAD_BALANCER_STRATEGY, AGENT_HEALTH_CHECK_INTERVAL
from src.logging import setup_logger
from src.database import get_session, close_session
from src.database.models import AgentModel

logger = setup_logger(__name__)


class LoadBalancer:
    """Distributes tasks to agents based on selected strategy."""

    def __init__(self, strategy: str = LOAD_BALANCER_STRATEGY):
        self.strategy = strategy
        self.current_index = 0  # For round-robin
        logger.info(f"LoadBalancer initialized with strategy: {strategy}")

    def get_available_agents(self) -> List[AgentModel]:
        """
        Get list of healthy, online agents.
        
        Returns:
            List of AgentModel instances
        """
        session = get_session()
        try:
            # Filter: status = online and last heartbeat within health check interval
            threshold = datetime.utcnow() - timedelta(seconds=AGENT_HEALTH_CHECK_INTERVAL)
            agents = session.query(AgentModel).filter(
                AgentModel.status == "online",
                AgentModel.last_heartbeat >= threshold
            ).all()
            return agents
        finally:
            close_session(session)

    def select_agent(self) -> Optional[str]:
        """
        Select an agent based on strategy.
        
        Returns:
            Agent ID or None if no agents available
        """
        agents = self.get_available_agents()
        
        if not agents:
            logger.warning("No available agents for task assignment.")
            return None

        if self.strategy == "round_robin":
            return self._round_robin(agents)
        elif self.strategy == "least_busy":
            return self._least_busy(agents)
        elif self.strategy == "random":
            return self._random(agents)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, falling back to round-robin")
            return self._round_robin(agents)

    def _round_robin(self, agents: List[AgentModel]) -> str:
        """Round-robin: cycle through agents."""
        agent = agents[self.current_index % len(agents)]
        self.current_index += 1
        logger.info(f"Round-robin: Selected agent {agent.id}")
        return agent.id

    def _least_busy(self, agents: List[AgentModel]) -> str:
        """Least-busy: select agent with lowest tasks_failed / tasks_completed ratio."""
        # Sort by success rate (completed / (completed + failed))
        def success_rate(agent: AgentModel) -> float:
            total = agent.tasks_completed + agent.tasks_failed
            if total == 0:
                return 1.0  # Prioritize agents with no history
            return agent.tasks_completed / total

        sorted_agents = sorted(agents, key=success_rate, reverse=True)
        agent = sorted_agents[0]
        logger.info(f"Least-busy: Selected agent {agent.id} (success rate: {success_rate(agent):.2%})")
        return agent.id

    def _random(self, agents: List[AgentModel]) -> str:
        """Random: select random agent."""
        agent = random.choice(agents)
        logger.info(f"Random: Selected agent {agent.id}")
        return agent.id

    def report_agent_health(self, agent_id: str, is_healthy: bool):
        """Update agent health status."""
        session = get_session()
        try:
            agent = session.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if agent:
                agent.status = "online" if is_healthy else "offline"
                agent.last_heartbeat = datetime.utcnow()
                session.commit()
                logger.info(f"Agent {agent_id} health updated: {agent.status}")
        finally:
            close_session(session)


# Global load balancer instance
load_balancer = LoadBalancer()
