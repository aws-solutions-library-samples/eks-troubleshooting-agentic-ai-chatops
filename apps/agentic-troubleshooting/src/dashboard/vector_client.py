"""S3 Vectors client for dashboard operations."""

import boto3
import json
import os
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class VectorClient:
    """Client for interacting with S3 Vectors database."""
    
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.vector_bucket_name = os.getenv('VECTOR_BUCKET')
        self.vector_index_name = os.getenv('VECTOR_INDEX_NAME', 'k8s-troubleshooting')
        
        # Initialize clients
        self.s3vectors_client = boto3.client('s3vectors', region_name=self.aws_region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
    
    def list_all_vectors(self) -> List[Dict[str, Any]]:
        """List all vectors in the database."""
        try:
            response = self.s3vectors_client.list_vectors(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name
            )
            return response.get('vectors', [])
        except Exception as e:
            logger.error(f"Failed to list vectors: {e}")
            return []
    
    def get_vector_count(self) -> int:
        """Get total count of vectors."""
        try:
            vectors = self.list_all_vectors()
            return len(vectors)
        except Exception as e:
            logger.error(f"Failed to get vector count: {e}")
            return 0
    
    def search_vectors(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search vectors by similarity."""
        try:
            # Generate query embedding
            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": query})
            )
            embedding = json.loads(response["body"].read())["embedding"]
            
            # Query vector index
            response = self.s3vectors_client.query_vectors(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name,
                queryVector={"float32": embedding},
                topK=top_k,
                returnDistance=True,
                returnMetadata=True
            )
            
            return response.get('vectors', [])
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []
    
    def get_vector_details(self, vector_key: str) -> Dict[str, Any]:
        """Get detailed information about a specific vector."""
        try:
            response = self.s3vectors_client.get_vector(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name,
                key=vector_key,
                returnMetadata=True
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get vector details: {e}")
            return {}
    
    def delete_all_vectors(self) -> Tuple[bool, str]:
        """Delete all vectors from the database."""
        try:
            vectors = self.list_all_vectors()
            if not vectors:
                return True, "No vectors to delete"
            
            # Get all vector keys
            vector_keys = [v.get('key') for v in vectors if v.get('key')]
            
            if not vector_keys:
                return True, "No valid vector keys found"
            
            # Delete all vectors at once
            response = self.s3vectors_client.delete_vectors(
                vectorBucketName=self.vector_bucket_name,
                indexName=self.vector_index_name,
                keys=vector_keys
            )
            
            return True, f"Successfully deleted {len(vector_keys)} vectors"
            
        except Exception as e:
            error_msg = f"Failed to delete vectors: {str(e)}"
            logger.error(error_msg)
            return False, error_msg