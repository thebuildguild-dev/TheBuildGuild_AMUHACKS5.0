import os
import uuid
import asyncio
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime

# Document modules
from src.document.downloader import download_pdf
from src.document.validator import validate_pdf
from src.document.splitter import split_pdf
from src.utils.hashing import compute_sha256
from src.utils.file_utils import create_temp_dir, cleanup_directory

# Services
from src.services.gemini_extraction_service import extract_text_from_chunk
from src.services.metadata_service import detect_exam_papers
from src.services.embedding_service import embed_texts
from src.services.vector_service import ensure_collection, upsert_vectors, DEFAULT_COLLECTION_NAME
from src.services.ingestion_service import (
    update_job_status, check_document_exists, link_document_to_user, 
    save_document_metadata, save_chunk_metadata, save_papers
)

async def run_ingestion_pipeline(job_id: str, user_id: str, sources: List[Dict]):
    """
    Orchestrate the full ingestion pipeline.
    """
    work_dir = create_temp_dir(prefix=f"ingest_{job_id}_")
    
    # Init pipeline counters
    processed_count = 0
    success_count = 0
    duplicates_count = 0
    errors_list = []
    documents_list = []

    try:
        print(f"Starting pipeline for job {job_id}")
        ensure_collection()
        
        for idx, source in enumerate(sources):
            print(f"Processing source {idx+1}/{len(sources)}")
            processed_count += 1
            
            # 1. Download & 2. Validate
            file_path = None
            original_filename = source.get('filename', 'unknown.pdf')
            
            if source['type'] == 'url':
                result = download_pdf(source['value'], work_dir)
                if not result:
                    errors_list.append(f"Download failed for {source['value']}")
                    update_job_status(job_id, {
                        'processed': processed_count, 
                        'errors': errors_list
                    })
                    continue
                file_path, original_filename = result
            else:
                errors_list.append(f"Unsupported source type: {source['type']}")
                update_job_status(job_id, {
                    'processed': processed_count, 
                    'errors': errors_list
                })
                continue

            # 3. Compute SHA256
            sha256 = compute_sha256(file_path)
            
            # Check DB
            existing = check_document_exists(sha256)
            if existing:
                print(f"Document exists: {sha256}")
                link_document_to_user(user_id, sha256)
                
                success_count += 1
                duplicates_count += 1
                documents_list.append(sha256)
                
                update_job_status(job_id, {
                    'processed': processed_count,
                    'successful': success_count,
                    'duplicates': duplicates_count,
                    'documents': documents_list
                })
                continue

            # 4. Split PDF
            chunks = split_pdf(file_path, work_dir)
            
            # Document Metadata
            doc_info = {
                'sha256': sha256,
                'original_filename': original_filename,
                'total_pages': validate_pdf(file_path),
                'source_type': source['type'],
                'source_value': source.get('value') if source['type'] == 'url' else None
            }
            save_document_metadata(doc_info, user_id)

            # 5. Extract Text & 6. Detect Papers
            full_text_buffer = ""
            extracted_chunks = []
            
            for chunk in chunks:
                text = extract_text_from_chunk(chunk['path'], chunk)
                if text:
                    chunk['text_content'] = text
                    extracted_chunks.append(chunk)
                    # Add explicit page markers for the metadata detector
                    full_text_buffer += f"\n--- PAGE START: {chunk.get('page_start')} END: {chunk.get('page_end')} ---\n"
                    full_text_buffer += text + "\n\n"
            
            # Detect papers with page ranges
            papers_metadata = detect_exam_papers(full_text_buffer)
            paper_db_ids = save_papers(sha256, papers_metadata)

            # 7. Map text to paper (Filter papers per chunk)
            
            # 8. Generate Embeddings & 9. Store Vectors
            points_to_upsert = []
            
            for chunk in extracted_chunks:
                # Filter relevant papers for this chunk
                chunk_start = chunk.get('page_start', 1)
                chunk_end = chunk.get('page_end', 1)
                
                relevant_papers = []
                for paper in papers_metadata:
                    p_start = paper.get('start_page', 1)
                    p_end = paper.get('end_page', 9999)
                    
                    # Check overlap
                    if max(chunk_start, p_start) <= min(chunk_end, p_end):
                        relevant_papers.append(paper)

                # Embed
                embeddings = embed_texts([chunk['text_content']])
                if not embeddings: continue
                vector = embeddings[0]
                
                # Qdrant Point
                point_id = str(uuid.uuid4())
                payload = {
                    "text": chunk['text_content'],
                    "document_sha256": sha256,
                    "chunk_number": chunk['chunk_number'],
                    "page_start": chunk.get('page_start'),
                    "page_end": chunk.get('page_end'),
                    "papers": relevant_papers, # Store ONLY relevant papers
                    "filename": original_filename
                }
                
                points_to_upsert.append({
                    "id": point_id,
                    "vector": vector,
                    "payload": payload
                })
                
                # DB Store
                save_chunk_metadata(sha256, chunk, point_id, chunk['text_content'], paper_db_ids)

            # Upsert batch
            if points_to_upsert:
                upsert_vectors(points_to_upsert)

            success_count += 1
            documents_list.append(sha256)
            
            update_job_status(job_id, {
                "status": "completed", 
                "successful": success_count,
                "processed": processed_count,
                "documents": documents_list
            })

    except Exception as e:
        print(f"Pipeline failed: {e}")
        errors_list.append(str(e))
        update_job_status(job_id, {
            "status": "failed", 
            "errors": errors_list
        })
    finally:
        # Final status update ensures consistency
        update_job_status(job_id, {
            'processed': processed_count,
            'successful': success_count,
            'duplicates': duplicates_count,
            'errors': errors_list
        })
        cleanup_directory(work_dir)
