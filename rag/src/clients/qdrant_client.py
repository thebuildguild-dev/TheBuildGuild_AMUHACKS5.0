from qdrant_client import QdrantClient
from src.config import config

def get_qdrant_client() -> QdrantClient:
    """Create and return a Qdrant client instance"""
    try:
        if config.QDRANT_API_KEY:
            client = QdrantClient(
                host=config.QDRANT_HOST,
                port=config.QDRANT_PORT,
                api_key=config.QDRANT_API_KEY,
                https=False,
            )
        else:
            client = QdrantClient(
                host=config.QDRANT_HOST,
                port=config.QDRANT_PORT,
                https=False,
            )
        return client
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        raise
