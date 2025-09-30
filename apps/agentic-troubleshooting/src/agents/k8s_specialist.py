"""K8s specialist agent with embedded EKS MCP server."""
from strands import Agent
import logging
from src.tools.k8s_tools import describe_pod, get_pods
from src.config.settings import Config
from src.prompts import K8S_SPECIALIST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class K8sSpecialist:
    """K8s troubleshooting specialist with embedded EKS MCP server."""
    
    def __init__(self):
        """Initialize the K8s specialist with EKS MCP integration."""
        tools = [describe_pod, get_pods]
        
        cluster_info = f"Cluster: {getattr(Config, 'CLUSTER_NAME', 'unknown')} in region {Config.AWS_REGION}\n"
        
        self.system_prompt = f"{cluster_info}{K8S_SPECIALIST_SYSTEM_PROMPT}"
        
        self.agent = Agent(
            system_prompt=self.system_prompt,
            model=Config.BEDROCK_MODEL_ID,
            tools=tools
        )
    
    def troubleshoot(self, issue: str) -> str:
        """Troubleshoot a K8s issue with EKS cluster context."""
        try:
            return str(self.agent(issue)).strip()
        except Exception as e:
            logger.error(f"Error troubleshooting: {e}")
            return "Error during troubleshooting. Please try again."
    
    