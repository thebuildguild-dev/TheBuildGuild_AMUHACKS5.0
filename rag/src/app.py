from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import re
import json
from dotenv import load_dotenv
from src.qdrant_client import create_client

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AMU Recovery RAG Service",
    description="RAG service for Past Year Questions analysis",
    version="1.0.0"
)

# Qdrant client instance (singleton)
_qdrant_client = None

def get_qdrant_client():
    """Dependency injection for Qdrant client"""
    global _qdrant_client
    if _qdrant_client is None:
        try:
            _qdrant_client = create_client()
        except Exception as e:
            print(f" Failed to connect to Qdrant: {e}")
            raise HTTPException(status_code=503, detail="Qdrant service unavailable")
    
    return _qdrant_client


# Pydantic models
class QueryRequest(BaseModel):
    subject: str = Field(..., description="Subject name")
    query: str = Field(..., description="Natural language query or topic")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return")

class QueryResult(BaseModel):
    text: str
    score: float
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    success: bool
    results: List[QueryResult]
    analysis: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        client = get_qdrant_client()
        collections = client.get_collections()
        
        return {
            "ok": True,
            "status": "healthy",
            "service": "rag",
            "qdrant_collections": len(collections.collections),
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "unhealthy",
            "error": str(e),
        }


# Query endpoint
@app.post("/query", response_model=QueryResponse)
async def query_pyqs(
    request: QueryRequest,
    client: Any = Depends(get_qdrant_client)
):
    """
    Query RAG service for Past Year Questions
    Returns relevant PYQs with Gemini-powered analysis
    """
    try:
        # Import query modules
        from src.embedder import embed_texts, generate_text
        from src.qdrant_client import search_vectors
        
        print(f"Received query for subject: {request.subject}, query: {request.query}")
        
        # Generate embedding for query using embed_texts
        query_embeddings = embed_texts([request.query])
        query_vector = query_embeddings[0]
        
        # Search Qdrant in amu_pyq collection with subject filter
        collection_name = os.getenv("COLLECTION_NAME", "amu_pyq")
        
        # Filter by subject if provided
        filter_conditions = {"subject": request.subject} if request.subject else None
        
        search_results = search_vectors(
            client=client,
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=request.top_k,
            filter_conditions=filter_conditions
        )
        
        # Transform results
        results = []
        for hit in search_results:
            results.append(QueryResult(
                text=hit.payload.get("text", ""),
                score=hit.score,
                metadata={
                    "year": hit.payload.get("year"),
                    "subject": hit.payload.get("subject"),
                    "topic": hit.payload.get("topic"),
                    "marks": hit.payload.get("marks", 5),  # Default 5 marks
                    "difficulty": hit.payload.get("difficulty"),
                    "source_filename": hit.payload.get("source_filename"),
                }
            ))
        
        # Generate Gemini analysis
        analysis = None
        use_gemini_analysis = os.getenv("USE_GEMINI_ANALYSIS", "true").lower() == "true"
        
        if use_gemini_analysis and results:
            try:
                # Prepare context from top N results
                context_parts = []
                for idx, result in enumerate(results[:min(10, len(results))]):
                    context_parts.append(
                        f"[Question {idx + 1}]\n"
                        f"Text: {result.text[:400]}...\n"
                        f"Year: {result.metadata.get('year', 'Unknown')}\n"
                        f"Topic: {result.metadata.get('topic', 'Unknown')}\n"
                        f"Marks: {result.metadata.get('marks', 5)}\n"
                        f"Relevance Score: {result.score:.3f}\n"
                    )
                
                context_string = "\n\n".join(context_parts)
                
                # Craft analysis prompt
                analysis_prompt = f"""Analyze these retrieved past year exam questions for {request.subject} related to the query: "{request.query}"

Retrieved Questions:
{context_string}

Based on these questions, provide a comprehensive analysis in the following structured JSON format:

{{
  "topics": [
    {{
      "topic": "Topic name",
      "frequency": number (how many times it appears),
      "likely_marks": number (average marks allocation),
      "examples": ["brief example 1", "brief example 2"]
    }}
  ],
  "insights": "One paragraph explaining patterns in question types, difficulty trends, and key concepts that appear frequently",
  "recommended_focus": [
    "Specific area 1 to prioritize",
    "Specific area 2 to prioritize",
    "Specific area 3 to prioritize"
  ],
  "exam_strategy": "One paragraph with actionable advice on how to prepare for and approach these types of questions"
}}

Provide ONLY the JSON output, no additional text."""

                # Call Gemini LLM
                print(f"Generating Gemini analysis...")
                llm_response = generate_text(
                    prompt=analysis_prompt,
                    temperature=0.3,
                    max_output_tokens=1500
                )
                
                # Try to parse JSON from response (handle markdown code blocks)
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find raw JSON
                    json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                    json_str = json_match.group(0) if json_match else llm_response
                
                analysis = json.loads(json_str)
                print(f"Gemini analysis generated successfully")
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse Gemini response as JSON: {e}")
                analysis = {
                    "raw_response": llm_response,
                    "error": "Failed to parse structured analysis"
                }
            except Exception as e:
                print(f"Gemini analysis failed: {e}")
                analysis = None
        
        print(f"Query successful, returned {len(results)} results")
        
        return QueryResponse(
            success=True,
            results=results,
            analysis=analysis,
            metadata={
                "subject": request.subject,
                "query": request.query,
                "top_k": request.top_k,
                "collection": collection_name,
            }
        )
    
    except Exception as e:
        print(f" Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Statistics endpoint
@app.get("/stats")
async def get_statistics(client: Any = Depends(get_qdrant_client)):
    """Get RAG service statistics"""
    try:
        from src.qdrant_client import get_collection_info
        
        collections = client.get_collections()
        
        stats = {
            "collections": [],
            "total_vectors": 0,
        }
        
        for collection in collections.collections:
            try:
                info = get_collection_info(client, collection.name)
                stats["collections"].append({
                    "name": collection.name,
                    "vectors_count": info['vectors_count'],
                })
                stats["total_vectors"] += info['vectors_count'] or 0
            except:
                pass
        
        return stats
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Inspect data endpoint
@app.get("/inspect")
async def inspect_data(
    collection: str = "amu_pyq",
    limit: int = 5,
    client: Any = Depends(get_qdrant_client)
):
    """Inspect stored data in vector database"""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        from src.qdrant_client import get_collection_info
        
        # Get collection info
        info = get_collection_info(client, collection)
        
        # Scroll to get sample points
        scroll_result = client.scroll(
            collection_name=collection,
            limit=limit,
            with_payload=True,
            with_vectors=False  # Don't fetch large vectors for inspection
        )
        
        points = scroll_result[0]
        
        # Format sample data
        samples = []
        for point in points:
            sample = {
                "id": point.id,
                "metadata": {
                    k: v for k, v in point.payload.items() if k != 'text'
                },
                "text_preview": point.payload.get('text', '')[:200] + "..." if point.payload.get('text', '') else ""
            }
            samples.append(sample)
        
        # Count by year
        year_counts = {}
        years = ['2023-2024', '2024-2025', '2022-2023', '2021-2022']
        
        for year in years:
            try:
                count_result = client.count(
                    collection_name=collection,
                    count_filter=Filter(
                        must=[FieldCondition(key='year', match=MatchValue(value=year))]
                    )
                )
                if count_result.count > 0:
                    year_counts[year] = count_result.count
            except:
                pass
        
        # Count by subject
        subject_counts = {}
        subjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science', 'Unknown']
        
        for subject in subjects:
            try:
                count_result = client.count(
                    collection_name=collection,
                    count_filter=Filter(
                        must=[FieldCondition(key='subject', match=MatchValue(value=subject))]
                    )
                )
                if count_result.count > 0:
                    subject_counts[subject] = count_result.count
            except:
                pass
        
        return {
            "collection": collection,
            "info": info,
            "sample_data": samples,
            "statistics": {
                "by_year": year_counts,
                "by_subject": subject_counts
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {str(e)}")

@app.post("/ingest")
async def ingest_documents(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    urls: Optional[str] = Form(default=None),
    files: Optional[List[UploadFile]] = File(default=None),
    client: Any = Depends(get_qdrant_client)
):
    """
    Ingest documents from URLs or file uploads
    Runs as async background job
    """
    try:
        from src.document_ingest import create_job, ingest_documents_async
        
        # Parse URLs if provided
        url_list = []
        if urls:
            try:
                url_list = json.loads(urls)
            except:
                url_list = [urls]
        
        # Validate input
        if not url_list and not files:
            raise HTTPException(
                status_code=400,
                detail="Must provide either URLs or file uploads"
            )
        
        # Prepare sources list
        sources = []
        
        # Add URLs
        for url in url_list:
            sources.append({
                'type': 'url',
                'value': url,
                'filename': url.split('/')[-1]
            })
        
        # Add file uploads
        if files:
            for file in files:
                file_content = await file.read()
                sources.append({
                    'type': 'file',
                    'value': file_content,
                    'filename': file.filename
                })
        
        # Create job
        job_id = create_job(user_id, len(sources))
        
        print(f"Created ingestion job {job_id} for user {user_id}")
        print(f"  Sources: {len(url_list)} URLs, {len(files) if files else 0} files")
        
        # Start background processing
        background_tasks.add_task(
            ingest_documents_async,
            job_id,
            user_id,
            sources,
            client
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Document ingestion started",
            "total_sources": len(sources)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/jobs/{job_id}")
async def get_ingestion_status(job_id: str, user_id: str):
    """Get status of document ingestion job"""
    try:
        from src.document_ingest import get_job_status
        
        status = get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user owns this job
        if status['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "AMU Recovery RAG Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "ingest": "POST /ingest",
            "jobs": "GET /jobs/{job_id}",
            "query": "POST /query",
            "stats": "GET /stats",
            "inspect": "GET /inspect?collection=amu_pyq&limit=5",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
