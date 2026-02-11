import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Qdrant Configuration
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "") or None
    
    # Gemini Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", "gemini-2.5-flash")
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Vector Configuration
    VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "3072"))
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "examintel_pyq")
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS = ["*"] if os.getenv("CORS_ALLOW_METHODS", "*") == "*" else os.getenv("CORS_ALLOW_METHODS", "*").split(",")
    CORS_ALLOW_HEADERS = ["*"] if os.getenv("CORS_ALLOW_HEADERS", "*") == "*" else os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        return True

config = Config()
