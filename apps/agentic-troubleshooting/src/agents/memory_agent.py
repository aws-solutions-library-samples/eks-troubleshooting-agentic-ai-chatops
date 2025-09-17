"""Fast memory agent for quick retrieval and storage."""

import logging
import json
import boto3
from strands import Agent, tool
from src.config.settings import Config
from src.prompts import MEMORY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Initialize clients
bedrock = boto3.client("bedrock-runtime", region_name=Config.AWS_REGION)
s3vectors = boto3.client("s3vectors", region_name=Config.AWS_REGION)

VECTOR_BUCKET = Config.VECTOR_BUCKET
INDEX_NAME = Config.INDEX_NAME

class MemoryAgent:
    """K8s troubleshooting memory agent using S3 Vectors."""
    
    def __init__(self):
        self.agent = Agent(
            system_prompt=MEMORY_SYSTEM_PROMPT,
            model=Config.BEDROCK_MODEL_ID,
            tools=[store_solution, retrieve_solutions]
        )
        
@tool
def store_solution(query: str, solution: str, metadata: dict = None) -> str:
    """Store a K8s troubleshooting solution in vector database."""
    try:
        # Generate embedding
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": query})
        )
        embedding = json.loads(response["body"].read())["embedding"]
        
        # Store in S3 Vectors
        s3vectors.put_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            vectors=[{
                "key": f"solution_{hash(query)}",
                "data": {"float32": embedding},
                "metadata": {
                    "query": query,
                    "solution": solution,
                    **(metadata or {})
                }
            }]
        )
        return "Solution stored successfully"
    except Exception as e:
        logger.error(f"Store error: {e}")
        return f"Failed to store: {e}"

@tool
def retrieve_solutions(query: str, top_k: int = 3) -> str:
    """Retrieve similar K8s troubleshooting solutions."""
    try:
        # Generate query embedding
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": query})
        )
        embedding = json.loads(response["body"].read())["embedding"]
        
        # Query vector index
        response = s3vectors.query_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            queryVector={"float32": embedding},
            topK=top_k,
            returnDistance=True,
            returnMetadata=True
        )
        
        if not response.get("vectors"):
            return "No similar solutions found"
        
        result = "Similar solutions found:\n\n"
        for i, vector in enumerate(response["vectors"], 1):
            metadata = vector["metadata"]
            result += f"{i}. Query: {metadata['query']}\n"
            result += f"   Solution: {metadata['solution']}\n"
            result += f"   Distance: {vector.get('distance', 'N/A')}\n\n"
        
        return result
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        return f"Failed to retrieve: {e}"