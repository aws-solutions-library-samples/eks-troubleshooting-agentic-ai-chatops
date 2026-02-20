"""K8s specialist agent with EKS Hosted MCP."""
from strands import Agent
import logging
from src.tools.k8s_tools import describe_pod, get_pods
from src.config.settings import Config
from src.prompts import K8S_SPECIALIST_SYSTEM_PROMPT
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient

logger = logging.getLogger(__name__)


class K8sSpecialist:
    """K8s troubleshooting specialist with EKS Hosted MCP."""
    
    def __init__(self):
        """Initialize the K8s specialist with EKS Hosted MCP."""
        tools = [describe_pod, get_pods]
        
        self.eks_mcp_client = None
        self._mcp_connected = False
        
        # Add EKS Hosted MCP if enabled
        if Config.ENABLE_EKS_MCP:
            try:
                # Get temporary credentials from Pod Identity and create AWS credentials file
                import os
                import boto3
                
                home_dir = os.path.expanduser("~")
                aws_dir = os.path.join(home_dir, ".aws")
                os.makedirs(aws_dir, exist_ok=True)
                
                # Get credentials from boto3 (which uses Pod Identity)
                session = boto3.Session()
                credentials = session.get_credentials()
                frozen_creds = credentials.get_frozen_credentials()
                
                # Create credentials file
                credentials_path = os.path.join(aws_dir, "credentials")
                with open(credentials_path, "w") as f:
                    f.write(f"[default]\n")
                    f.write(f"aws_access_key_id = {frozen_creds.access_key}\n")
                    f.write(f"aws_secret_access_key = {frozen_creds.secret_key}\n")
                    if frozen_creds.token:
                        f.write(f"aws_session_token = {frozen_creds.token}\n")
                
                # Create config file
                config_path = os.path.join(aws_dir, "config")
                with open(config_path, "w") as f:
                    f.write(f"[default]\n")
                    f.write(f"region = {Config.AWS_REGION}\n")
                
                logger.info(f"Created AWS credentials at {credentials_path} for Pod Identity")
                
                # Use EKS Hosted MCP via proxy
                mcp_url = f"https://eks-mcp.{Config.AWS_REGION}.api.aws/mcp"
                
                args_list = [
                    "mcp-proxy-for-aws@latest",
                    mcp_url,
                    "--service", "eks-mcp",
                    "--region", Config.AWS_REGION,
                    "--profile", "default"
                ]
                
                # Add read-only flag if write is disabled
                if not Config.ALLOW_WRITE:
                    args_list.append("--read-only")
                
                self.eks_mcp_client = MCPClient(
                    lambda: stdio_client(
                        StdioServerParameters(
                            command="uvx",
                            args=args_list
                        )
                    )
                )
                
                self.eks_mcp_client.__enter__()
                self._mcp_connected = True
                eks_mcp_tools = self.eks_mcp_client.list_tools_sync()
                
                tools.extend(eks_mcp_tools)
                logger.info(f"EKS MCP enabled with {len(eks_mcp_tools)} tools")
            except Exception as e:
                logger.error(f"Failed to initialize EKS MCP: {e}")
    
        cluster_info = f"Cluster: {Config.CLUSTER_NAME} in region {Config.AWS_REGION}\n"
        
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
    
    def __del__(self):
        """Clean up MCP connection."""
        if self._mcp_connected and self.eks_mcp_client:
            try:
                self.eks_mcp_client.__exit__(None, None, None)
            except:
                pass