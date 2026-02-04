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
