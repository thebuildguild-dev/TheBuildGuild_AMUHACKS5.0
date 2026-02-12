from typing import List
import hashlib
from src.config import config
from src.clients.gemini_client import get_gemini_client, generate_content_with_retry
from src.clients.redis_client import cache_get, cache_set

def embed_texts(texts: List[str], model: str = None) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Gemini with caching
    """
    if not texts:
        return []    
    if model is None:
        model = config.GEMINI_EMBEDDING_MODEL
    
    # Check cache for each text
    all_embeddings = []
    uncached_texts = []
    uncached_indices = []
    text_to_indices = {}  # Map text to all its indices (for deduplication)
    
    for idx, text in enumerate(texts):
        cache_key = f"embedding:{model}:{hashlib.sha256(text.encode()).hexdigest()}"
        cached_embedding = cache_get(cache_key)
        
        if cached_embedding is not None:
            # Validate cached embedding is a list
            if not isinstance(cached_embedding, list):
                print(f"Warning: Invalid cached embedding format for text {idx}")
                cached_embedding = None
        
        if cached_embedding is not None:
            all_embeddings.append(cached_embedding)
        else:
            all_embeddings.append(None)
            
            # Track this text needs embedding (deduplicate later)
            if text not in text_to_indices:
                text_to_indices[text] = []
                uncached_texts.append(text)
            text_to_indices[text].append(idx)
            uncached_indices.append(idx)
    
    # Generate embeddings for uncached texts (deduplicated)
    if uncached_texts:
        client = get_gemini_client()
        try:
            batch_size = 100
            new_embeddings = []
            
            for i in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[i:i + batch_size]
                result = client.models.embed_content(
                    model=model,
                    contents=batch,
                )
                
                if not hasattr(result, 'embeddings') or not result.embeddings:
                    raise RuntimeError("No embeddings returned from Gemini API")
                
                new_embeddings.extend([e.values for e in result.embeddings])
            
            # Validate embedding count matches deduplicated text count
            if len(new_embeddings) != len(uncached_texts):
                raise ValueError(f"Embedding count mismatch: expected {len(uncached_texts)}, got {len(new_embeddings)}")
            
            # Cache new embeddings and insert into results for ALL occurrences of each text
            for text_idx, (text, embedding) in enumerate(zip(uncached_texts, new_embeddings)):
                # Cache the embedding
                cache_key = f"embedding:{model}:{hashlib.sha256(text.encode()).hexdigest()}"
                cache_set(cache_key, embedding, ttl=2592000)  # 30 days
                
                # Update all positions where this text appears
                for original_idx in text_to_indices[text]:
                    all_embeddings[original_idx] = embedding
                
        except Exception as e:
            print(f"Embedding failed: {e}")
            raise e
    
    return all_embeddings
