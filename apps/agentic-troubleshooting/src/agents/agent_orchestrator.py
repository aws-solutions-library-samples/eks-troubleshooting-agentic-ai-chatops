from strands import Agent, tool
from src.agents.k8s_specialist import K8sSpecialist
from src.config.settings import Config
from src.prompts import ORCHESTRATOR_SYSTEM_PROMPT, K8S_KEYWORDS
import logging
# from uuid import uuid4

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """Direct K8s troubleshooting orchestrator."""
    
    def __init__(self):
        self.k8s_specialist = K8sSpecialist()
        
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
        
    
    def respond(self, message: str, thread_id: str, context: str = None) -> str:
        """Main entry point for responses."""
        try:
            agent_response = self.agent(message)
            
            if hasattr(agent_response, 'content'):
                response = str(agent_response.content).strip()
            elif hasattr(agent_response, 'text'):
                response = str(agent_response.text).strip()
            elif isinstance(agent_response, (list, tuple)):
                response = ' '.join(str(part) for part in agent_response).strip()
            else:
                response = str(agent_response).strip()
            
            logger.info(f"Full agent response: {response[:200]}..." if len(response) > 200 else f"Full agent response: {response}")
            
            return response if response else "I'm here to help with Kubernetes troubleshooting. How can I assist you?"
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return "Error processing request. Please try again."
        
    def should_respond(self, message: str, is_mention: bool = False, is_thread: bool = False) -> bool:
        """Check if should respond to message using Nova Micro or keyword fallback."""
        if is_mention:
            return True
        
        if is_thread:
            return True
        
        return any(keyword in message.lower() for keyword in K8S_KEYWORDS)