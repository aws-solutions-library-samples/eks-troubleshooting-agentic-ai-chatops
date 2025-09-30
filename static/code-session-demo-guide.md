# EKS Troubleshooting Agent - Live Coding Demo Guide

## 🎯 Demo Overview
This demo showcases the evolution from basic Kubernetes tools to an intelligent multi-agent system with MCP integration and tribal knowledge storage.

---

## 📋 Demo Flow

### **STEP 1: Project Architecture Overview** 🏗️

**🎤 Talking Points:**
- Explain the Strands-based multi-agent architecture
- Show project structure and key components

**📁 Key Files to Highlight:**
```
src/agents/
├── agent_orchestrator.py    # Main orchestrator
├── k8s_specialist.py        # K8s specialist agent
config/settings.py           # Configuration
prompts.py                   # System prompts
slack_handler.py            # Slack integration
```

**🔍 Current Architecture:**
- **Orchestrator Agent**: Routes user requests to specialized agents
- **K8s Specialist Agent**: Handles Kubernetes troubleshooting (local tools only)

---

### **STEP 2: Basic Slack Interaction Demo** 💬

**🎤 Demo Script:**
1. Show Slack integration working
2. Try: `"List all namespaces in the cluster"`
3. **Expected Result**: Agent fails - no access to cluster

**💡 Key Point**: Agent is limited to local tools only

---

### **STEP 3: Enable EKS MCP Integration** 🔧

#### **File 1: `config/settings.py`**
**📝 Add these properties:**
```python
@property
def ENABLE_EKS_MCP(self) -> bool:
    return os.getenv('ENABLE_EKS_MCP', 'false').lower() == 'true'

@property
def EKS_MCP_ALLOW_WRITE(self) -> bool:
    return os.getenv('EKS_MCP_ALLOW_WRITE', 'false').lower() == 'true'
```

#### **File 2: `agents/k8s_specialist.py`**

**📝 Step 3a: Add Imports**
```python
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient
import boto3
import os
```

**📝 Step 3b: Update `__init__` Method**
*Add this code inside the constructor:*
```python
self.eks_mcp_client = None
self._mcp_connected = False

# Add EKS MCP server if enabled
if Config.ENABLE_EKS_MCP:
    try:
        # Get AWS credentials from the current session (Pod Identity)
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Create EKS MCP client with explicit credentials
        env_vars = {
            "AWS_REGION": Config.AWS_REGION,
            "FASTMCP_LOG_LEVEL": "ERROR"
        }
        
        # Pass explicit AWS credentials if available
        if credentials:
            env_vars["AWS_ACCESS_KEY_ID"] = credentials.access_key
            env_vars["AWS_SECRET_ACCESS_KEY"] = credentials.secret_key
            if credentials.token:
                env_vars["AWS_SESSION_TOKEN"] = credentials.token
            logger.info("Using Pod Identity credentials for EKS MCP server")
        else:
            # Fallback to environment credentials
            for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"]:
                if key in os.environ:
                    env_vars[key] = os.environ[key]
            logger.info("Using environment credentials for EKS MCP server")
        
        # Use kubeconfig created by init container
        env_vars["KUBECONFIG"] = "/shared/kubeconfig"
        
        # Build args based on configuration
        args = ["awslabs.eks-mcp-server@latest", "--allow-sensitive-data-access"]
        if Config.EKS_MCP_ALLOW_WRITE:
            args.append("--allow-write")
        
        self.eks_mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=args,
                env=env_vars
            )
        ))
        
        # Connect and get EKS MCP tools
        self.eks_mcp_client.__enter__()
        self._mcp_connected = True
        eks_tools = self.eks_mcp_client.list_tools_sync()
        tools.extend(eks_tools)
        logger.info(f"Added {len(eks_tools)} EKS MCP tools with persistent connection")
            
    except Exception as e:
        logger.warning(f"Failed to initialize EKS MCP: {e}")
        self.eks_mcp_client = None
```

**📝 Step 3c: Add Cleanup Method**
*Add after the troubleshoot method:*
```python
def __del__(self):
    """Clean up MCP connection."""
    if self._mcp_connected and self.eks_mcp_client:
        try:
            self.eks_mcp_client.__exit__(None, None, None)
        except:
            pass
```

---

### **STEP 4: Test MCP Integration** ✅

**🎤 Demo Script:**
1. Restart the application
2. Try: `"List all namespaces in the cluster"`
3. **Expected Result**: Success! Agent can now access EKS cluster

**💡 Key Point**: MCP provides real-time cluster access

---

### **STEP 5: Demonstrate Agent Limitations** ⚠️

**🎤 Demo Script:**
1. Try: `"What version of EKS am I running?"`
2. **Expected Result**: Agent refuses to respond (keyword-based filtering)

**💡 Key Point**: Current system uses simple keyword matching

---

### **STEP 6: Implement Smart Classification with Nova Micro** 🧠

#### **File 1: `prompts.py`**
**📝 Add Classification Prompt:**
```python
# Nova Micro Classification Prompt
CLASSIFICATION_PROMPT = """Is this message related to Kubernetes, system troubleshooting, technical issues, or requests for help? 

Message: "{message}"

Respond with only "YES" or "NO"."""
```

#### **File 2: `agents/agent_orchestrator.py`**

**📝 Step 6a: Update Imports**
```python
from src.prompts import ORCHESTRATOR_SYSTEM_PROMPT, CLASSIFICATION_PROMPT, K8S_KEYWORDS
import json
import boto3
```

**📝 Step 6b: Update Constructor**
```python
def __init__(self):
    self.k8s_specialist = K8sSpecialist()

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
    )
```

**📝 Step 6c: Add Nova Classification Method**
```python
def _classify_with_nova(self, message: str) -> bool:
    """Use Amazon Nova Micro to classify if message is K8s/troubleshooting related."""
    try:
        prompt = CLASSIFICATION_PROMPT.format(message=message)
        
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 10,
                "temperature": 0.1
            }
        }
        
        response = self.bedrock_client.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        logger.info(f"Message classification should respond:{result}")
        
        answer = result['output']['message']['content'][0]['text'].strip().upper()
        
        return answer == "YES"
        
    except Exception as e:
        logger.error(f"Nova classification failed: {e}")
        # Fallback to keyword matching
        return any(keyword in message.lower() for keyword in K8S_KEYWORDS)
```

**📝 Step 6d: Update `should_respond` Method**
*Add this at the beginning of the method:*
```python
# Try Nova Micro classification first
if self.bedrock_client:
    return self._classify_with_nova(message)
```

---

### **STEP 7: Test Smart Classification** 🎯

**🎤 Demo Script:**
1. Try: `"What version of EKS am I running?"`
2. **Expected Result**: Agent now responds intelligently!

**💡 Key Point**: Nova Micro provides intelligent message classification

---

### **STEP 8: Introduce Tribal Knowledge Concept** 📚

**🎤 Talking Points:**
- Explain the need for persistent knowledge storage
- Show S3 Vector Database (empty initially)
- Introduce Memory Agent concept

---

### **STEP 9: Implement Memory Agent Server** 🧠

#### **Create New File: `agents/memory_agent_server.py`**
```python
"""Memory Agent A2A Server for K8s troubleshooting knowledge storage and retrieval."""

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
import boto3
import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MemoryAgentServer:
    """Memory agent for storing and retrieving K8s troubleshooting solutions."""
    
    def __init__(self):
        # Environment variables
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
        self.vector_bucket_name = os.getenv('VECTOR_BUCKET')
        self.vector_index_name = os.getenv('INDEX_NAME', 'k8s-troubleshooting')
        
        # Initialize S3 Vectors client
        try:
            self.s3vectors_client = boto3.client('s3vectors', region_name=self.aws_region)
        except Exception as e:
            logger.error(f"Failed to initialize S3 Vectors client: {e}")
            self.s3vectors_client = None
        
        # Memory system prompt
        memory_prompt = """You are a K8s troubleshooting memory specialist. Your role:

1. STORE solutions: When given troubleshooting solutions, extract key information and store in S3 vectors
2. RETRIEVE solutions: When given problems, search for similar past solutions and return ALL details found
3. Only do what you are asked to do, nothing more, if it is retrieve just retrieve, if it is save, just save
4. For storage: Extract problem description, solution steps, and relevant K8s resources
5. Format responses for Slack bold is single *  (DO NOT USE MARKDOWN)
6. Always return the solution, along with a message that you have stored"""
        
        # Create Strands agent with memory tools
        self.agent = Agent(
            name="Memory Agent",
            description="A memory agent that stores and retrieves K8s troubleshooting solutions using S3 Vectors.",
            system_prompt=memory_prompt,
            model=self.bedrock_model_id,
            tools=[self.store_solution, self.retrieve_solution]
        )
    
    @tool
    def store_solution(self, problem_description: str, solution_steps: str, k8s_resources: str = "") -> str:
        """Store a K8s troubleshooting solution in S3 Vectors."""
        if not self.s3vectors_client:
            return "S3 Vectors client not available"
        
        try:
            # Create document content
            content = f"Problem: {problem_description}\nSolution: {solution_steps}\nResources: {k8s_resources}"
            
            # Generate embedding
            import boto3
            bedrock = boto3.client('bedrock-runtime', region_name=self.aws_region)
            response = bedrock.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": problem_description})
            )
            embedding = json.loads(response["body"].read())["embedding"]
            
            # Store in S3 Vectors
            response = self.s3vectors_client.put_vectors(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name,
                vectors=[{
                    "key": f"solution_{hash(problem_description)}",
                    "data": {"float32": embedding},
                    "metadata": {
                        "content": content,
                        "problem": problem_description,
                        "type": "k8s_solution"
                    }
                }]
            )
            
            return f"Solution stored successfully"
            
        except Exception as e:
            logger.error(f"Failed to store solution: {e}")
            return f"Failed to store solution: {str(e)}"
    
    @tool
    def retrieve_solution(self, problem_query: str, max_results: int = 3) -> str:
        """Retrieve similar K8s troubleshooting solutions from S3 Vectors."""
        if not self.s3vectors_client:
            return "S3 Vectors client not available"
        
        try:
            # Generate query embedding
            import boto3
            bedrock = boto3.client('bedrock-runtime', region_name=self.aws_region)
            response = bedrock.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": problem_query})
            )
            embedding = json.loads(response["body"].read())["embedding"]
            
            # Query vector index
            response = self.s3vectors_client.query_vectors(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name,
                queryVector={"float32": embedding},
                topK=max_results,
                returnDistance=True,
                returnMetadata=True
            )
            
            if not response.get('vectors'):
                return "No similar solutions found in memory"
            
            # Format results
            solutions = []
            for i, vector in enumerate(response['vectors'], 1):
                metadata = vector['metadata']
                distance = vector.get('distance', 0)
                solutions.append(f"*Solution {i}* (Distance: {distance:.2f}):\n{metadata.get('content', 'No content')}")
            
            return "\n\n".join(solutions)
            
        except Exception as e:
            logger.error(f"Failed to retrieve solutions: {e}")
            return f"Failed to retrieve solutions: {str(e)}"

def main():
    """Start the Memory Agent A2A server."""
    # Create memory agent server
    memory_server = MemoryAgentServer()
    
    # Create A2A server
    a2a_server = A2AServer(agent=memory_server.agent)
    
    print("Starting Memory Agent A2A Server on http://localhost:9000")
    
    # Start the server
    a2a_server.serve()

if __name__ == "__main__":
    main()
```

---

### **STEP 10: Test Memory Agent Locally** 🧪

**🎤 Demo Script:**
1. Run memory agent server locally
2. Test store and retrieve functionality
3. Verify S3 Vector Database integration

---

### **STEP 11: Integrate Memory Agent with Orchestrator** 🔗

#### **File: `agents/agent_orchestrator.py`**

**📝 Step 11a: Add A2A Import**
```python
from strands_tools.a2a_client import A2AClientToolProvider
```

**📝 Step 11b: Add Memory Agent Tool**
```python
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
```

**📝 Step 11c: Update Constructor**
```python
def __init__(self):
    self.k8s_specialist = K8sSpecialist()
    
    self.agent = Agent(
        name="K8s Orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        model=Config.BEDROCK_MODEL_ID,
        tools=[self.troubleshoot_k8s, self.memory_agent_provider]
    )
```

**📝 Step 11d: Update System Prompt in `prompts.py`**
```python
ORCHESTRATOR_SYSTEM_PROMPT = """You are a K8s troubleshooting orchestrator with A2A memory capabilities:

1. Check memory first: Use memory_agent_provider to search for similar issues (A2A - discover agent and tools)
2. Return found solutions: If memory has solutions, return that content directly to user
3. Troubleshoot new issues: If no memory found, use troubleshoot_k8s to solve
4. Save valuable solutions: After successful troubleshooting, save with memory_agent_provider (A2A)
5. Save knowledge sharing: If user shares solutions/tips (not questions), save directly to build tribal knowledge
6. Format for Slack: Use single * for bold, no markdown
7. Always return solutions, never storage confirmations"""
```

---

### **STEP 12: Deploy and Test Complete System** 🚀

**🎤 Demo Script:**
1. Deploy using `demo/deploy.sh`
2. Run orchestrator + k8s specialist using `main.py`
3. Run memory agent server in `agents/memory_agent_server.py`
4. Test complete troubleshooting workflow with memory

---

### **STEP 13: Final Demo - Tribal Knowledge in Action** 🎭

**🎤 Demo Scenarios:**
1. **First Issue**: Ask about a K8s problem (no memory exists)
2. **Agent Troubleshoots**: Watch agent solve and store solution
3. **Second Issue**: Ask similar problem (memory retrieval works)
4. **Knowledge Sharing**: Share a tip and watch it get stored
5. **Show S3 Dashboard**: Demonstrate tribal knowledge growth

**💡 Key Points:**
- Memory-first approach reduces troubleshooting time
- Tribal knowledge builds over time
- A2A architecture enables modular agent design
- MCP provides real-time cluster access

---

## 🎯 Demo Success Metrics

- ✅ Basic Slack integration working
- ✅ MCP integration enables cluster access
- ✅ Nova Micro improves message classification
- ✅ Memory agent stores and retrieves solutions
- ✅ A2A architecture connects all components
- ✅ Complete troubleshooting workflow functional

---

## 🔧 Quick Reference Commands

**Start Memory Agent Server:**
```bash
cd agents/
python memory_agent_server.py
```

**Start Main Application:**
```bash
python main.py
```

**Deploy Demo Environment:**
```bash
cd demo/
./deploy.sh
```

---

## 📝 Notes for Presenter

- Keep code changes minimal and focused
- Explain each architectural decision
- Show before/after comparisons
- Highlight the evolution from simple to intelligent
- Emphasize real-world applicability
- Be prepared for questions about scalability and security