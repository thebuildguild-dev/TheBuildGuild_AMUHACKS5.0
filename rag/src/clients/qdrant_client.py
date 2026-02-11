import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
if QDRANT_API_KEY == "":
    QDRANT_API_KEY = None

def get_qdrant_client() -> QdrantClient:
    """Create and return a Qdrant client instance"""
    try:
        if QDRANT_API_KEY:
            client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                api_key=QDRANT_API_KEY,
                https=False,
            )
        else:
            client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                https=False,
            )
        return client
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        raise
