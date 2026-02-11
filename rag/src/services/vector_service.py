from typing import List, Dict, Any, Optional
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchAny
from src.clients.qdrant_client import get_qdrant_client
from src.config import config

def ensure_collection(collection_name: str = None, vector_size: int = 3072):
    """Ensure Qdrant collection exists"""
    if collection_name is None:
        collection_name = config.COLLECTION_NAME
    client = get_qdrant_client()
    try:
        if not client.collection_exists(collection_name):
             client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
             print(f"Created collection {collection_name}")
    except Exception as e:
        print(f"Error ensuring collection: {e}")

def upsert_vectors(points: List[Dict[str, Any]], collection_name: str = DEFAULT_COLLECTION_NAME):
    """Upsert vectors to Qdrant"""
    client = get_qdrant_client()
    if not points:
        return
    
    qdrant_points = [
        PointStruct(
            id=p['id'],
            vector=p['vector'],
            payload=p.get('payload', {})
        ) for p in points
    ]
    
    try:
        client.upsert(
            collection_name=collection_name,
            points=qdrant_points
        )
    except Exception as e:
        print(f"Vector upsert failed: {e}")
        raise

def search_vectors(
    query_vector: List[float], 
    limit: int = 5, 
    collection_name: str = DEFAULT_COLLECTION_NAME,
    document_sha256_filter: Optional[List[str]] = None
):
    """
    Search for similar vectors with optional filtering by document SHA256.
    
    Args:
        query_vector: The embedding vector to search for
        limit: Maximum number of results to return
        collection_name: Qdrant collection name
        document_sha256_filter: Optional list of SHA256 hashes to filter results by user's accessible documents
    """
    client = get_qdrant_client()
    try:
        query_filter = None
        if document_sha256_filter:
            # Filter to only include vectors from user's documents
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_sha256",
                        match=MatchAny(any=document_sha256_filter)
                    )
                ]
            )
        
        return client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        ).points
    except Exception as e:
        print(f"Vector search failed: {e}")
        raise
