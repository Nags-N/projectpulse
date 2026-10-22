"""Agent registration and heartbeat client."""

import logging
import httpx

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class RegistrationClient:
    def __init__(self, config: AgentConfig):
        self.config = config

    def register(self) -> bool:
        """Register the agent with the central backend."""
        url = f"{self.config.backend_url.rstrip('/')}/api/agents/register"
        payload = {
            "agent_id": self.config.agent_id,
            "user_id": self.config.user_id,
            "project_id": self.config.project_id,
            "role": self.config.role,
            "machine_name": self.config.machine_name,
            "machine_id": self.config.machine_id,
        }
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.post(url, json=payload)
                if res.status_code in (200, 201):
                    logger.info("Agent %s successfully registered with backend", self.config.agent_id)
                    return True
                logger.warning("Agent registration returned status %d: %s", res.status_code, res.text)
        except Exception as exc:
            logger.warning("Could not reach backend to register agent %s: %s", self.config.agent_id, exc)
        return False

    def heartbeat(self) -> bool:
        """Send alive heartbeat to the central backend."""
        url = f"{self.config.backend_url.rstrip('/')}/api/agents/heartbeat"
        payload = {
            "agent_id": self.config.agent_id,
            "monitoring_active": self.config.monitoring_active,
        }
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.post(url, json=payload)
                return res.status_code == 200
        except Exception:
            return False
