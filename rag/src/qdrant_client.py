"""
Qdrant Client Module
Wraps Qdrant vector database operations
"""
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from dotenv import load_dotenv

load_dotenv()

# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")  # Default to empty string instead of None
if QDRANT_API_KEY == "":
    QDRANT_API_KEY = None  # Convert empty string to None for Qdrant client
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "3072"))  # gemini-embedding-001 produces 3072-dim vectors


def create_client() -> QdrantClient:
    """
    Create and return a Qdrant client instance
    
    Returns:
        QdrantClient instance
    """
    try:
        if QDRANT_API_KEY:
            client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                api_key=QDRANT_API_KEY,
                https=False,  # Explicitly disable HTTPS for local Docker setup
            )
        else:
            client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                https=False,  # Explicitly disable HTTPS for local Docker setup
            )
        
        print(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        return client
    
    except Exception as e:
        print(f" Failed to connect to Qdrant: {e}")
        raise


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = VECTOR_SIZE,
    distance: Distance = Distance.COSINE
) -> bool:
    """
    Ensure a collection exists, create if it doesn't
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection
        vector_size: Dimension of vectors (default: 3072 for Gemini)
        distance: Distance metric (default: COSINE)
    
    Returns:
        True if collection exists or was created successfully
    """
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if collection_name in collection_names:
            print(f"Collection '{collection_name}' already exists")
            return True
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )
        
        print(f"Created collection '{collection_name}' (size: {vector_size}, distance: {distance.value})")
        return True
    
    except Exception as e:
        print(f" Error ensuring collection '{collection_name}': {e}")
        raise


def upsert_vectors(
    client: QdrantClient,
    collection_name: str,
    points: List[Dict[str, Any]],
    batch_size: int = 100
) -> int:
    """
    Upsert vectors into a collection
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection
        points: List of point dictionaries with structure:
            {
                'id': str or int,
                'vector': List[float],
                'payload': Dict[str, Any]
            }
        batch_size: Number of points to upsert in each batch
    
    Returns:
        Number of points successfully upserted
    """
    if not points:
        print("No points to upsert")
        return 0
    
    try:
        # Convert to PointStruct objects
        qdrant_points = []
        for point in points:
            if not isinstance(point.get('id'), (str, int)):
                point['id'] = str(point.get('id', ''))
            
            qdrant_point = PointStruct(
                id=point['id'],
                vector=point['vector'],
                payload=point.get('payload', {})
            )
            qdrant_points.append(qdrant_point)
        
        # Upsert in batches
        total_upserted = 0
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i:i + batch_size]
            
            client.upsert(
                collection_name=collection_name,
                points=batch,
            )
            
            total_upserted += len(batch)
            print(f"Upserted batch {i // batch_size + 1} ({len(batch)} points)")
        
        print(f"Total upserted: {total_upserted} points to collection '{collection_name}'")
        return total_upserted
    
    except Exception as e:
        print(f" Error upserting vectors to '{collection_name}': {e}")
        raise


def search_vectors(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    top_k: int = 10,
    filter_conditions: Optional[Dict[str, Any]] = None,
    score_threshold: Optional[float] = None
) -> List[Any]:
    """
    Search for similar vectors in a collection
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection
        query_vector: Query vector (embedding)
        top_k: Number of results to return
        filter_conditions: Optional filter dict, e.g., {'year': '2024', 'subject': 'Math'}
        score_threshold: Minimum similarity score (0-1)
    
    Returns:
        List of search results (ScoredPoint objects)
    """
    try:
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            if must_conditions:
                query_filter = Filter(must=must_conditions)
        
        # Perform vector search using query_points
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold,
        ).points
        
        print(f"Found {len(search_result)} results in collection '{collection_name}'")
        return search_result
    
    except Exception as e:
        print(f" Error searching in collection '{collection_name}': {e}")
        raise


def search_qdrant(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    limit: int = 10,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[Any]:
    """
    Alias for search_vectors with simpler parameter names
    Used by app.py
    """
    return search_vectors(
        client=client,
        collection_name=collection_name,
        query_vector=query_vector,
        top_k=limit,
        filter_conditions=filter_dict
    )


def delete_collection(client: QdrantClient, collection_name: str) -> bool:
    """
    Delete a collection
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection to delete
    
    Returns:
        True if deleted successfully
    """
    try:
        client.delete_collection(collection_name=collection_name)
        print(f"Deleted collection '{collection_name}'")
        return True
    except Exception as e:
        print(f" Error deleting collection '{collection_name}': {e}")
        raise


def get_collection_info(client: QdrantClient, collection_name: str) -> Dict[str, Any]:
    """
    Get information about a collection
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection
    
    Returns:
        Dictionary with collection information
    """
    try:
        collection = client.get_collection(collection_name=collection_name)
        
        # Access points_count from the collection info
        vectors_count = collection.points_count if hasattr(collection, 'points_count') else 0
        if hasattr(collection, 'vectors_count'):
            vectors_count = collection.vectors_count
        
        info = {
            "name": collection_name,
            "vectors_count": vectors_count,
            "points_count": vectors_count,
            "status": collection.status,
            "config": {
                "vector_size": collection.config.params.vectors.size if hasattr(collection.config.params, 'vectors') else VECTOR_SIZE,
                "distance": collection.config.params.vectors.distance.value if hasattr(collection.config.params, 'vectors') else 'Cosine',
            }
        }
        
        return info
    except Exception as e:
        print(f" Error getting collection info for '{collection_name}': {e}")
        raise


def restore_from_dump(
    client: QdrantClient,
    dump_path: str,
    collection_name: Optional[str] = None
) -> bool:
    """
    Restore Qdrant data from a snapshot/dump file
    
    Note: Qdrant uses snapshots rather than dumps. This function attempts
    to restore from a snapshot file.
    
    Args:
        client: QdrantClient instance
        dump_path: Path to the snapshot/dump file
        collection_name: Optional collection name to restore
    
    Returns:
        True if restore was successful
    """
    try:
        import shutil
        import requests
        
        if not os.path.exists(dump_path):
            raise FileNotFoundError(f"Dump file not found: {dump_path}")
        
        print(f"Attempting to restore from {dump_path}")
        
        # Qdrant snapshot restore via HTTP API
        # This is a simplified approach - actual implementation may vary
        # based on Qdrant version and setup
        
        if collection_name:
            # Restore specific collection snapshot
            url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection_name}/snapshots/upload"
            
            with open(dump_path, 'rb') as f:
                response = requests.post(url, files={'snapshot': f})
            
            if response.status_code == 200:
                print(f"Restored collection '{collection_name}' from snapshot")
                return True
            else:
                print(f" Snapshot restore failed: {response.text}")
                return False
        else:
            # Full backup restore - typically requires Qdrant restart
            # This is a placeholder for actual implementation
            print("Full backup restore not implemented via API")
            print("Please refer to Qdrant documentation for full backup restoration")
            return False
    
    except Exception as e:
        print(f" Error restoring from dump: {e}")
        raise


def create_snapshot(
    client: QdrantClient,
    collection_name: str,
    output_dir: str = "./snapshots"
) -> str:
    """
    Create a snapshot of a collection
    
    Args:
        client: QdrantClient instance
        collection_name: Name of the collection
        output_dir: Directory to save snapshot
    
    Returns:
        Path to the created snapshot file
    """
    try:
        import requests
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Create snapshot via API
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection_name}/snapshots"
        response = requests.post(url)
        
        if response.status_code == 200:
            snapshot_name = response.json()['result']['name']
            
            # Download snapshot
            download_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection_name}/snapshots/{snapshot_name}"
            snapshot_response = requests.get(download_url)
            
            snapshot_path = os.path.join(output_dir, snapshot_name)
            with open(snapshot_path, 'wb') as f:
                f.write(snapshot_response.content)
            
            print(f"Created snapshot: {snapshot_path}")
            return snapshot_path
        else:
            raise Exception(f"Snapshot creation failed: {response.text}")
    
    except Exception as e:
        print(f" Error creating snapshot: {e}")
        raise


def list_collections(client: QdrantClient) -> List[str]:
    """
    List all collections in Qdrant
    
    Args:
        client: QdrantClient instance
    
    Returns:
        List of collection names
    """
    try:
        collections = client.get_collections().collections
        collection_names = [col.name for col in collections]
        print(f"Found {len(collection_names)} collections")
        return collection_names
    except Exception as e:
        print(f" Error listing collections: {e}")
        raise
