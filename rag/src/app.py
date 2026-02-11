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


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Robustly extract the outer-most JSON object from text using a stack-based approach.
    Handles nested braces correctly, unlike simple regex.
    """
    if not text:
        return None
        
    text = text.strip()
    
    # Find the start of the JSON object
    start_idx = text.find('{')
    if start_idx == -1:
        return None
        
    stack = 0
    in_string = False
    escape = False
    
    for i, char in enumerate(text[start_idx:], start=start_idx):
        if escape:
            escape = False
            continue
            
        if char == '\\':
            escape = True
            continue
            
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                stack += 1
            elif char == '}':
                stack -= 1
                if stack == 0:
                    return text[start_idx : i+1]
    
    return None

def fallback_parse_analysis(text: str) -> Dict[str, Any]:
    """
    Attempt to extract information from malformed JSON or raw text.
    """
    analysis = {
        "topics": [],
        "insights": "Analysis generated, but structural parsing failed.",
        "recommended_focus": [],
        "exam_strategy": "Review the raw analysis below.",
        "parsing_error": True
    }
    
    try:
        # 1. Try to extract "insights"
        # Look for "insights": "..." OR "insights": '...'
        insights_match = re.search(r'"insights"\s*:\s*"(.*?)(?<!\\)"', text, re.DOTALL)
        if not insights_match:
             insights_match = re.search(r'"insights"\s*:\s*\'(.*?)(?<!\\)\'', text, re.DOTALL)
             
        if insights_match:
            analysis['insights'] = insights_match.group(1).replace('\\"', '"').replace("\\'", "'")
            
        # 2. Try to extract "exam_strategy"
        strategy_match = re.search(r'"exam_strategy"\s*:\s*"(.*?)(?<!\\)"', text, re.DOTALL)
        if not strategy_match:
             strategy_match = re.search(r'"exam_strategy"\s*:\s*\'(.*?)(?<!\\)\'', text, re.DOTALL)
             
        if strategy_match:
            analysis['exam_strategy'] = strategy_match.group(1).replace('\\"', '"').replace("\\'", "'")
            
        # 3. Try to extract simple topics list if the complex structure failed
        # Look for "topic": "Name"
        topic_names = re.findall(r'"topic"\s*:\s*"(.*?)(?<!\\)"', text)
        if topic_names:
            seen = set()
            for name in topic_names:
                if name not in seen:
                    analysis['topics'].append({
                        "topic": name,
                        "frequency": "N/A",  # Lost in parsing
                        "likely_marks": "N/A"
                    })
                    seen.add(name)
        
        # 4. Try to extract recommended_focus
        # This is usually a list of strings: "recommended_focus": ["A", "B"]
        focus_block_match = re.search(r'"recommended_focus"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if focus_block_match:
            content = focus_block_match.group(1)
            # Extract strings
            items = re.findall(r'"(.*?)(?<!\\)"', content)
            analysis['recommended_focus'] = items
            
        # Check if we successfully extracted anything
        if analysis['insights'] or analysis['topics'] or analysis['exam_strategy']:
            analysis['parsing_error'] = False
            
    except Exception as e:
        print(f"Fallback parsing also encountered error: {e}")
        
    return analysis


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
                
                # Check if response is empty or too short
                if not llm_response or len(llm_response.strip()) < 10:
                    print(f"Gemini returned empty or very short response")
                    raise ValueError("Empty response from Gemini")
                
                print(f"📝 Gemini response preview: {llm_response[:150]}...")
                
                # Try to parse JSON from response using robust extraction
                json_str = extract_json_from_text(llm_response)
                
                if json_str:
                    print("✓ Extracted potential JSON object using stack-based parser")
                    try:
                        analysis = json.loads(json_str)
                        print(f"✅ Gemini analysis generated successfully")
                    except json.JSONDecodeError as e:
                        print(f"Extracted JSON is malformed: {e}")
                        print(f"   Attempted to parse: {json_str[:300]}...")
                        print("🔄 Attempting fallback parsing on extracted segment...")
                        analysis = fallback_parse_analysis(json_str)
                        if analysis.get('parsing_error'):
                            print("🔄 Fallback on segment failed, attempting on full response...")
                            analysis = fallback_parse_analysis(llm_response)
                else:
                    print("No JSON structure found in response")
                    print("🔄 Attempting fallback parsing on full response...")
                    analysis = fallback_parse_analysis(llm_response)
                    
                if analysis.get('parsing_error'):
                     print("Parsing still marked as error after fallback")
                else:
                     print("✅ Fallback parsing retrieved partial data")
            except (ValueError, Exception) as e:
                error_msg = str(e)
                print(f"Gemini analysis failed: {error_msg}")
                
                # Provide user-friendly message based on error type
                if "503" in error_msg or "UNAVAILABLE" in error_msg or "high demand" in error_msg:
                    analysis = {
                        "error": "AI analysis temporarily unavailable",
                        "reason": "High demand on Gemini API - service will retry automatically",
                        "note": "Query results are still valid and usable"
                    }
                elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    analysis = {
                        "error": "Rate limit reached",
                        "reason": "API quota exceeded - please try again in a moment",
                        "note": "Query results are still valid and usable"
                    }
                else:
                    analysis = {
                        "error": "Analysis generation failed",
                        "reason": error_msg[:200],
                        "note": "Query results are still valid and usable"
                    }
        
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
