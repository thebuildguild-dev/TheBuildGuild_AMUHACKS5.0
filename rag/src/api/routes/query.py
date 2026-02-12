from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import hashlib
import json
from src.config import config
from src.services.vector_service import search_vectors
from src.services.embedding_service import embed_texts
from src.services.ingestion_service import get_user_documents
from src.clients.redis_client import cache_get, cache_set

router = APIRouter()

class QueryRequest(BaseModel):
    user_id: str
    query: str
    subject: Optional[str] = None
    top_k: int = 5

class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]] = None

@router.post("/query", response_model=QueryResponse)
async def search(request: QueryRequest):
    """
    Semantic search over ingested papers (user-specific)
    """
    try:
        # Get user's accessible documents
        user_documents = get_user_documents(request.user_id)
        
        # Generate cache key from query + sorted user documents
        sorted_docs = sorted(user_documents) if user_documents else []
        cache_key_data = {
            "query": request.query,
            "subject": request.subject,
            "top_k": request.top_k,
            "documents": sorted_docs
        }
        cache_key = f"query:{hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
        
        # Check cache first
        cached_result = cache_get(cache_key)
        if cached_result:
            return cached_result
        
        if not user_documents:
            return {
                "results": [],
                "analysis": {
                    "topics": [],
                    "insights": "No PYQs available. Please upload some past year question papers to get started.",
                    "difficulty": "N/A"
                }
            }
        
        # Generate embedding
        embeddings = embed_texts([request.query])
        if not embeddings:
            raise HTTPException(status_code=500, detail="Embedding generation failed")
            
        vector = embeddings[0]

        # Search with user document filter
        results = search_vectors(
            vector, 
            limit=request.top_k,
            document_sha256_filter=user_documents
        )
        
        if not results:
            return {
                "results": [],
                "analysis": {
                    "topics": [],
                    "insights": "No matching questions found in your uploaded PYQs for this query.",
                    "difficulty": "N/A"
                }
            }
        
        # Relevance threshold check - filter out irrelevant queries
        RELEVANCE_THRESHOLD = 0.55
        if results[0].score < RELEVANCE_THRESHOLD:
            return {
                "results": [],
                "analysis": {
                    "topics": [],
                    "insights": "Your query doesn't seem related to academic exam topics from your uploaded PYQs. Please ask about subjects, concepts, or topics from your uploaded Past Year Questions (PYQs). For example: 'differential equations', 'circuit theory', 'data structures', etc.",
                    "difficulty": "N/A"
                }
            }
        
        # Format results
        formatted_results = []
        for res in results:
            formatted_results.append({
                "text": res.payload.get('text', ''),
                "score": res.score,
                "metadata": {
                    "filename": res.payload.get('filename'),
                    "chunk": res.payload.get('chunk_number'),
                    "papers": res.payload.get('papers'),
                    "page_start": res.payload.get('page_start'),
                    "page_end": res.payload.get('page_end')
                }
            })
            
        # Analysis generation using Gemini
        analysis = None
        if formatted_results:
            try:
                from src.clients.gemini_client import generate_content_with_retry
                from google.genai import types
                import json

                # Construct context
                context_parts = []
                for i, r in enumerate(formatted_results):
                    meta = r['metadata']
                    papers = meta.get('papers')
                    if not papers: papers = []
                    
                    paper_info = ", ".join([p.get('subject', 'Unknown') for p in papers])
                    context_parts.append(f"Source {i+1} (Papers: {paper_info}):\n{r['text']}")
                
                context_str = "\n\n".join(context_parts)
                
                analysis_prompt = f"""
                You are an expert academic tutor. Based on the following retrieved exam question excerpts for the query '{request.query}', provide a structured analysis.
                
                Context:
                {context_str}
                
                Your task:
                1. Identify the key topics discussed in these questions.
                2. Provide strategic insights for a student preparing for these topics (e.g. common patterns, important concepts).
                3. Infer the difficulty level based on the questions.
                
                Return a JSON object with:
                - "topics": [List of key topics],
                - "insights": "A paragraph of strategic advice",
                - "difficulty": "Easy/Medium/Hard"
                """
                
                response = generate_content_with_retry(
                    model=config.GEMINI_GENERATION_MODEL,
                    contents=[analysis_prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                
                if response and response.text:
                    try:
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        analysis = json.loads(clean_text)
                    except json.JSONDecodeError:
                         analysis = {
                            "topics": ["Error parsing analysis"],
                            "insights": response.text,
                            "difficulty": "Unknown"
                         }

            except Exception as e:
                print(f"Analysis generation failed: {e}")
                analysis = {
                    "topics": [],
                    "insights": "Analysis service unavailable.",
                    "difficulty": "Unknown"
                }

        result = {
            "results": formatted_results,
            "analysis": analysis
        }
        
        # Cache the result
        cache_set(cache_key, result)
        
        return result

    except Exception as e:
        print(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
