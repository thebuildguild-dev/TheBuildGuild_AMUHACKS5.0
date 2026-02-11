from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from src.services.ingestion_service import create_job, get_job_status
from src.pipelines.ingest_pipeline import run_ingestion_pipeline

router = APIRouter()

class IngestUrlRequest(BaseModel):
    user_id: str
    urls: List[str]

class JobResponse(BaseModel):
    job_id: str
    status: str

@router.post("/ingest/url", response_model=JobResponse)
async def ingest_url(
    background_tasks: BackgroundTasks,
    request: IngestUrlRequest
):
    """Ingest from URLs"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
        
    job_id = create_job(request.user_id, total_sources=len(request.urls))
    
    sources = [{'type': 'url', 'value': url} for url in request.urls]
    
    background_tasks.add_task(run_ingestion_pipeline, job_id, request.user_id, sources)
    
    return {"job_id": job_id, "status": "processing"}

@router.get("/ingest/status/{job_id}")
async def job_status(job_id: str):
    """Get ingestion job status"""
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
