from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.api.routes import ingest, query, health

app = FastAPI(
    title="ExamIntel RAG Service",
    description="AI-powered PYQ intelligence using RAG and Gemini",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS,
    allow_headers=config.CORS_ALLOW_HEADERS,
)

# Include Routers
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(health.router, tags=["Health"])

@app.get("/")
def root():
    return {"message": "ExamIntel RAG Service is running"}
