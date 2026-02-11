from typing import List
from src.config import config
from src.clients.gemini_client import get_gemini_client, generate_content_with_retry

def embed_texts(texts: List[str], model: str = None) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Gemini
    """
    if not texts:
        return []    
    if model is None:
        model = config.GEMINI_EMBEDDING_MODEL
    client = get_gemini_client()
    try:
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = client.models.embed_content(
                model=model,
                contents=batch,
            )
            if hasattr(result, 'embeddings'):
                 all_embeddings.extend([e.values for e in result.embeddings])
            
        return all_embeddings

    except Exception as e:
        print(f"Embedding failed: {e}")
        # Fallback or retry logic could go here
        raise e
