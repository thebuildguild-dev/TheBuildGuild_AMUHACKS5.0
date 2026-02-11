from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from src.api.routes import ingest, query, health

load_dotenv()

app = FastAPI(
    title="ExamIntel RAG Service",
    description="AI-powered PYQ intelligence using RAG and Gemini",
    version="1.0.0"
)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_allow_methods = os.getenv("CORS_ALLOW_METHODS", "*")
cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "*")

if cors_allow_methods == "*":
    cors_allow_methods = ["*"]
else:
    cors_allow_methods = cors_allow_methods.split(",")

if cors_allow_headers == "*":
    cors_allow_headers = ["*"]
else:
    cors_allow_headers = cors_allow_headers.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
)

# Include Routers
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(health.router, tags=["Health"])

@app.get("/")
def root():
    return {"message": "ExamIntel RAG Service is running"}
