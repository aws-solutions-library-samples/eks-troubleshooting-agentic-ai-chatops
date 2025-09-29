from strands import Agent, tool
from src.agents.k8s_specialist import K8sSpecialist
# from src.agents.memory_agent import MemoryAgent
from src.config.settings import Config
from src.prompts import ORCHESTRATOR_SYSTEM_PROMPT, CLASSIFICATION_PROMPT, K8S_KEYWORDS
import logging
import boto3
import json
from uuid import uuid4
from strands_tools.a2a_client import A2AClientToolProvider

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """Direct K8s troubleshooting orchestrator."""
    
    def __init__(self):
        self.k8s_specialist = K8sSpecialist()
        # self.memory_agent = MemoryAgent()

        # Initialize Bedrock client for Nova Micro classification
        try:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=Config.AWS_REGION)
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client, falling back to keywords: {e}")
            self.bedrock_client = None
        
        self.agent = Agent(
            name="K8s Orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            model=Config.BEDROCK_MODEL_ID,
            tools=[self.troubleshoot_k8s]
            # tools=[self.troubleshoot_k8s, self.memory_operations]
            # tools=[self.troubleshoot_k8s, self.memory_agent_provider] #A2A
        )
        
    @tool
    def troubleshoot_k8s(self, query: str) -> str:
        """Perform K8s troubleshooting."""
        try:
            return self.k8s_specialist.troubleshoot(query)
        except Exception as e:
            return f"Troubleshooting error: {e}"

    # Local memory agent
    @tool
    def memory_operations(self, request: str) -> str:
        """Handle memory operations - store or retrieve K8s troubleshooting information."""
        try:
            result = self.memory_agent.agent(request)
            return str(result)
        except Exception as e:
            logger.error(f"Memory operation failed: {e}")
            return f"Memory error: {e}"
    
    # A2A tool
    @tool
    def memory_agent_provider(self, request: str) -> str:
        """Handle Memory agent connection using a2aclienttoolprovider
        
        Args:
            request (str): The request to send to the memory agent
            
        Returns:
            str: Response from the memory agent
            
        Raises:
            Exception: If memory agent connection fails
        """
        try:
            # Initialize provider with memory agent URL
            provider = A2AClientToolProvider(known_agent_urls=[Config.MEMORY_AGENT_SERVER_URL])
            logger.debug(f"Initialized memory agent provider: {provider}")
            
            # Get available tools from provider
            tools = provider.tools
            logger.debug(f"Available memory agent tools: {tools}")        
            
            # Create agent with tools and system prompt
            agent = Agent(
                tools=tools,
                system_prompt="You are a memory agent interface. Discover agents and tools you can use"
            )
            
            # Send request and get response
            response = agent(request)
            logger.info(f"Memory agent response received for request: {request[:100]}...")
            
            return str(response)
            
        except Exception as e:
            logger.error(f"Memory agent operation failed: {e}")
            raise Exception(f"Failed to process memory agent request: {str(e)}")        
    
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
        
        # Try Nova Micro classification first
        # if self.bedrock_client:
        #     return self._classify_with_nova(message)
        
        return any(keyword in message.lower() for keyword in K8S_KEYWORDS)

    # def _classify_with_nova(self, message: str) -> bool:
    #     """Use Amazon Nova Micro to classify if message is K8s/troubleshooting related."""
    #     try:
    #         prompt = CLASSIFICATION_PROMPT.format(message=message)
            
    #         body = {
    #             "messages": [
    #                 {
    #                     "role": "user",
    #                     "content": [{"text": prompt}]
    #                 }
    #             ],
    #             "inferenceConfig": {
    #                 "maxTokens": 10,
    #                 "temperature": 0.1
    #             }
    #         }
            
    #         response = self.bedrock_client.invoke_model(
    #             modelId="amazon.nova-micro-v1:0",
    #             body=json.dumps(body)
    #         )
            
    #         result = json.loads(response['body'].read())
    #         logger.info(f"Message classification should respond:{result}")
            
    #         answer = result['output']['message']['content'][0]['text'].strip().upper()
            
    #         return answer == "YES"
            
    #     except Exception as e:
    #         logger.error(f"Nova classification failed: {e}")
    #         # Fallback to keyword matching
    #         return any(keyword in message.lower() for keyword in K8S_KEYWORDS)