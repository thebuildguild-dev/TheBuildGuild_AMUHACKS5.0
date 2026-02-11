from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.routes import ingest, query, health

load_dotenv()

app = FastAPI(
    title="AMU Recovery RAG Service",
    description="RAG service for Past Year Questions analysis using Gemini",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(health.router, tags=["Health"])

@app.get("/")
def root():
    return {"message": "AMU Recovery RAG Service is running"}
