from strands import Agent, tool
from src.agents.k8s_specialist import K8sSpecialist
from src.config.settings import Config
from src.config.telemetry import setup_langfuse_telemetry
from src.prompts import ORCHESTRATOR_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)

# Initialize telemetry if enabled
setup_langfuse_telemetry()

class AgentSilentException(Exception):
    """Exception that should not generate error responses."""
    pass

class OrchestratorAgent:
    """Direct K8s troubleshooting orchestrator."""
    
    def __init__(self):
        self.k8s_specialist = K8sSpecialist()
        self.last_user_message = None
            
        self.agent = Agent(
            name="K8s Orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            model=Config.BEDROCK_MODEL_ID,
            tools=[self.troubleshoot_k8s]
        )
        
    @tool
    def troubleshoot_k8s(self, query: str) -> str:
        """Perform K8s troubleshooting."""
        try:
            return self.k8s_specialist.troubleshoot(query)
        except Exception as e:
            return f"Troubleshooting error: {e}"