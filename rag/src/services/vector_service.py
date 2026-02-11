import os
from typing import List, Dict, Any, Optional
from qdrant_client.models import VectorParams, Distance, PointStruct
from src.clients.qdrant_client import get_qdrant_client

# Default configuration
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "3072"))

DEFAULT_COLLECTION_NAME = os.getenv("COLLECTION_NAME", "amu_pyq")

def ensure_collection(collection_name: str = DEFAULT_COLLECTION_NAME, vector_size: int = 3072):
    """Ensure Qdrant collection exists"""
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

def search_vectors(query_vector: List[float], limit: int = 5, collection_name: str = DEFAULT_COLLECTION_NAME):
    """Search for similar vectors"""
    client = get_qdrant_client()
    try:
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
    except Exception as e:
        print(f"Vector search failed: {e}")
        raise
