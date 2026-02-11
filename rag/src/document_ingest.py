"""
Document ingestion handler with async job processing
"""
import os
import uuid
import asyncio
import tempfile
import shutil
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from src.document_processor import process_document, extract_text_with_gemini, detect_exam_papers
from src.embedder import embed_texts
from src.qdrant_client import ensure_collection
from qdrant_client.models import PointStruct
import json

# Job status tracking (in-memory for demo, use Redis/DB for production)
_job_status = {}

# PostgreSQL connection
def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def create_job(user_id: str, total_sources: int) -> str:
    """Create a new ingestion job"""
    job_id = str(uuid.uuid4())
    _job_status[job_id] = {
        'job_id': job_id,
        'user_id': user_id,
        'status': 'processing',
        'total_sources': total_sources,
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'duplicates': 0,
        'errors': [],
        'documents': [],
        'created_at': datetime.utcnow().isoformat(),
    }
    return job_id


def update_job_status(job_id: str, updates: Dict):
    """Update job status"""
    if job_id in _job_status:
        _job_status[job_id].update(updates)


def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status"""
    return _job_status.get(job_id)


async def check_document_exists(sha256_hash: str) -> Optional[Dict]:
    """Check if document already exists in database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT * FROM documents WHERE sha256_hash = %s",
            (sha256_hash,)
        )
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return dict(result) if result else None
    
    except Exception as e:
        print(f"Database check error: {e}")
        return None


async def link_document_to_user(user_id: str, sha256_hash: str):
    """Link existing document to user"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            INSERT INTO user_documents (user_id, document_sha256)
            VALUES (%s, %s)
            ON CONFLICT (user_id, document_sha256) DO NOTHING
            """,
            (user_id, sha256_hash)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Linked document {sha256_hash[:8]}... to user {user_id}")
    
    except Exception as e:
        print(f"Database link error: {e}")
        raise


async def save_document_metadata(doc_info: Dict, user_id: str):
    """Save document metadata to PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print(f"Saving document metadata for SHA: {doc_info['sha256']}")

        # Insert document - Use DO UPDATE to ensure we get an ID back and row exists
        cur.execute(
            """
            INSERT INTO documents (sha256_hash, original_filename, total_pages, upload_source, source_url, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sha256_hash) 
            DO UPDATE SET status = EXCLUDED.status
            RETURNING id
            """,
            (
                doc_info['sha256'],
                doc_info['original_filename'],
                doc_info['total_pages'],
                doc_info['source_type'],
                doc_info.get('source_value'),
                'completed'
            )
        )
        
        result = cur.fetchone()
        if not result:
            print(f"⚠️ Warning: No ID returned for document {doc_info['sha256']}")
        
        doc_id = result['id'] if result else None
        
        # Link to user
        cur.execute(
            """
            INSERT INTO user_documents (user_id, document_sha256)
            VALUES (%s, %s)
            ON CONFLICT (user_id, document_sha256) DO NOTHING
            """,
            (user_id, doc_info['sha256'])
        )
        
        conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"Saved document metadata: {doc_info['sha256'][:8]}... (ID: {doc_id})")
        return doc_id
    
    except Exception as e:
        print(f"Database save error: {e}")
        raise


async def save_chunk_metadata(doc_sha256: str, chunk_info: Dict, qdrant_id: str, text_content: str, paper_ids: List[str]):
    """Save document chunk metadata to PostgreSQL with many-to-many paper links"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert chunk without paper_id FK
        cur.execute(
            """
            INSERT INTO document_chunks 
            (document_sha256, chunk_number, page_range_start, page_range_end, qdrant_point_id, text_content)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_sha256, chunk_number) 
            DO UPDATE SET qdrant_point_id = EXCLUDED.qdrant_point_id 
            RETURNING id
            """,
            (
                doc_sha256,
                chunk_info['chunk_number'],
                chunk_info['page_start'],
                chunk_info['page_end'],
                qdrant_id,
                text_content[:5000]
            )
        )
        
        result = cur.fetchone()
        chunk_db_id = result['id'] if result else None
        
        if not chunk_db_id:
             # Try to fetch if insert failed (though ON CONFLICT DO UPDATE handles it, sometimes no RETURNING if no change?)
             cur.execute("SELECT id FROM document_chunks WHERE document_sha256 = %s AND chunk_number = %s", 
                        (doc_sha256, chunk_info['chunk_number']))
             res = cur.fetchone()
             chunk_db_id = res['id'] if res else None

        if chunk_db_id and paper_ids:
            # Insert links into join table
            for p_id in paper_ids:
                if not p_id: continue
                cur.execute(
                    """
                    INSERT INTO chunk_papers (chunk_id, paper_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (chunk_db_id, p_id)
                )

        conn.commit()
        cur.close()
        conn.close()
    
    except Exception as e:
        print(f"Chunk metadata save error: {e}")


async def ingest_documents_async(
    job_id: str,
    user_id: str,
    sources: List[Dict],
    qdrant_client
):
    """
    Async document ingestion process
    Handles download, validation, deduplication, splitting, extraction, and vector storage
    """
    work_dir = tempfile.mkdtemp(prefix=f"doc_ingest_{job_id}_")
    
    try:
        print(f"\nStarting document ingestion job {job_id}")
        print(f"   User: {user_id}")
        print(f"   Sources: {len(sources)}")
        print(f"   Work dir: {work_dir}")
        
        collection_name = os.getenv("COLLECTION_NAME", "amu_pyq")
        
        # Ensure collection exists
        ensure_collection(qdrant_client, collection_name)
        
        for idx, source in enumerate(sources):
            try:
                print(f"\nProcessing source {idx + 1}/{len(sources)}")
                
                # Process document ( download/validate/split)
                doc_info = process_document(source, user_id, work_dir)
                
                if 'error' in doc_info:
                    update_job_status(job_id, {
                        'processed': _job_status[job_id]['processed'] + 1,
                        'failed': _job_status[job_id]['failed'] + 1,
                        'errors': _job_status[job_id]['errors'] + [doc_info['error']]
                    })
                    continue
                
                # Check for duplicates
                existing_doc = await check_document_exists(doc_info['sha256'])
                
                if existing_doc:
                    print(f"Document already exists (SHA256: {doc_info['sha256'][:8]}...)")
                    print(f"   Linking to user {user_id}")
                    
                    # Just link to user
                    await link_document_to_user(user_id, doc_info['sha256'])
                    
                    update_job_status(job_id, {
                        'processed': _job_status[job_id]['processed'] + 1,
                        'successful': _job_status[job_id]['successful'] + 1,
                        'duplicates': _job_status[job_id]['duplicates'] + 1,
                        'documents': _job_status[job_id]['documents'] + [doc_info['sha256']]
                    })
                    continue
                
                # New document - process chunks
                print(f"New document - processing {len(doc_info['chunks'])} chunk(s)")
                
                # Step 1: Extract text from all chunks to detect papers
                print("Extracting text and detecting papers...")
                extracted_chunks = []
                full_text_buffer = ""
                
                # Pre-extract all text
                for chunk in doc_info['chunks']:
                     text = extract_text_with_gemini(chunk['path'], chunk)
                     if text and len(text) >= 50:
                         chunk['text_content'] = text
                         full_text_buffer += text + "\n\n"
                         extracted_chunks.append(chunk)
                     else:
                        print(f"Skipping chunk {chunk['chunk_number']} - insufficient text")

                # Step 2: Detect papers
                detected_papers = detect_exam_papers(full_text_buffer)
                
                # Save document metadata BEFORE papers to satisfy FK constraints
                await save_document_metadata(doc_info, user_id)

                # Step 3: Save detected papers
                saved_papers = await save_papers_metadata(doc_info['sha256'], detected_papers)

                # Step 4: Link chunks to papers and save to Qdrant/DB
                successful_chunks = []
                
                for chunk in extracted_chunks:
                    text_content = chunk['text_content']
                    
                    # Find matching paper IDs (Primary and All)
                    all_overlaps = find_all_overlapping_papers(chunk, saved_papers)
                    primary_paper_id = find_matching_paper(chunk, saved_papers)
                    chunk['paper_id'] = primary_paper_id
                    
                    # Generate embedding
                    embeddings = embed_texts([text_content])
                    embedding_vector = embeddings[0]
                    
                    # Create Qdrant point
                    point_id = str(uuid.uuid4())
                    
                    # Construct rich metadata arrays
                    paper_ids = []
                    subjects = []
                    subject_codes = []
                    semester_infos = []
                    
                    for p in all_overlaps:
                        if p.get('id'): paper_ids.append(p['id'])
                        if p.get('subject'): subjects.append(p['subject'])
                        if p.get('subject_code'): subject_codes.append(p['subject_code'])
                        
                        # Build semantic semester info
                        info_parts = [
                            p.get('program'),
                            p.get('semester'), 
                            p.get('exam_session'),
                            p.get('academic_year')
                        ]
                        # Join non-empty parts
                        sem_info = " ".join([part for part in info_parts if part])
                        if sem_info:
                            semester_infos.append(sem_info)

                    payload = {
                            "text": text_content,
                            "document_sha256": doc_info['sha256'],
                            "chunk_number": chunk['chunk_number'],
                            "page_range": f"{chunk['page_start']}-{chunk['page_end']}",
                            "original_filename": doc_info['original_filename'],
                            "total_pages": doc_info['total_pages'],
                            # Use arrays for multi-paper support
                            "paper_ids": paper_ids,
                            "subjects": subjects,
                            "subject_codes": subject_codes,
                            "semester_infos": semester_infos
                    }

                    point = PointStruct(
                        id=point_id,
                        vector=embedding_vector,
                        payload=payload
                    )
                    
                    # Upload to Qdrant
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=[point]
                    )
                    
                    print(f"Chunk {chunk['chunk_number']} uploaded to Qdrant (Paper ID: {primary_paper_id})")
                    
                    # Store chunk info for PostgreSQL save later
                    successful_chunks.append({
                        'chunk_info': chunk,
                        'point_id': point_id,
                        'text_content': text_content,
                        'paper_ids': paper_ids
                    })
                
                # Only save to PostgreSQL if at least one chunk was successful
                if successful_chunks:
                    # Document metadata already saved above
                    
                    # Then save chunk metadata
                    for chunk_data in successful_chunks:
                        await save_chunk_metadata(
                            doc_info['sha256'],
                            chunk_data['chunk_info'],
                            chunk_data['point_id'],
                            chunk_data['text_content'],
                            chunk_data['paper_ids']
                        )
                    
                    update_job_status(job_id, {
                        'processed': _job_status[job_id]['processed'] + 1,
                        'successful': _job_status[job_id]['successful'] + 1,
                        'documents': _job_status[job_id]['documents'] + [doc_info['sha256']]
                    })
                    
                    print(f"Document {doc_info['sha256'][:8]}... completed with {len(successful_chunks)} chunk(s)")
                else:
                    print(f"No chunks were successfully processed for {doc_info['sha256'][:8]}...")
                    update_job_status(job_id, {
                        'processed': _job_status[job_id]['processed'] + 1,
                        'failed': _job_status[job_id]['failed'] + 1,
                        'errors': _job_status[job_id]['errors'] + ['No chunks processed successfully']
                    })
            
            except Exception as e:
                print(f"Source processing error: {e}")
                update_job_status(job_id, {
                    'processed': _job_status[job_id]['processed'] + 1,
                    'failed': _job_status[job_id]['failed'] + 1,
                    'errors': _job_status[job_id]['errors'] + [str(e)]
                })
        
        # Mark job as complete
        update_job_status(job_id, {'status': 'completed'})
        print(f"\nJob {job_id} completed")
    
    except Exception as e:
        print(f"\nJob {job_id} failed: {e}")
        update_job_status(job_id, {
            'status': 'failed',
            'errors': _job_status[job_id]['errors'] + [f"Job error: {str(e)}"]
        })
    
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(work_dir)
            print(f"Cleaned up work directory: {work_dir}")
        except Exception as e:
            print(f"Cleanup warning: {e}")

async def save_papers_metadata(doc_sha256: str, papers: List[Dict]):
    """Save detected papers to PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        saved_papers = []
        for p in papers:
            cur.execute(
                """
                INSERT INTO papers 
                (document_sha256, subject, subject_code, academic_year, semester, 
                 program, exam_session, credits, duration, start_page, end_page, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    doc_sha256,
                    p.get('subject'),
                    p.get('subject_code'),
                    p.get('academic_year'),
                    p.get('semester'),
                    p.get('program'),
                    p.get('exam_session'),
                    str(p.get('credits')) if p.get('credits') else None,
                    str(p.get('duration')) if p.get('duration') else None,
                    p.get('start_page_estimate'),
                    p.get('end_page_estimate'),
                    json.dumps(p)
                )
            )
            p_id = cur.fetchone()['id']
            p['id'] = str(p_id) # Add DB ID back to dict
            saved_papers.append(p)
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"Saved {len(saved_papers)} papers metadata")
        return saved_papers

    except Exception as e:
        print(f"Papers metadata save error: {e}")
        return papers # Return original list if save fails, but without IDs

def find_all_overlapping_papers(chunk_info: Dict, papers: List[Dict]) -> List[Dict]:
    """Find all papers that overlap with this chunk."""
    if not papers:
        return []

    # If only one paper exists, assume it matches everything (fallback for single-paper PDFs)
    if len(papers) == 1:
        return papers

    c_start = chunk_info['page_start']
    c_end = chunk_info['page_end']
    overlaps = []

    for p in papers:
        # Handle None or invalid values safely
        p_start = p.get('start_page_estimate')
        if p_start is None: p_start = 0
            
        p_end = p.get('end_page_estimate')
        if p_end is None: p_end = 9999

        # Calculate overlap
        overlap_start = max(c_start, p_start)
        overlap_end = min(c_end, p_end)

        if overlap_start <= overlap_end:
            overlaps.append(p)
            
    return overlaps

def find_matching_paper(chunk_info: Dict, papers: List[Dict]) -> Optional[str]:
    """
    Find which paper corresponds to this chunk.
    Returns the ID of the paper with the MAXIMUM overlap.
    """
    if not papers:
        return None
        
    # If only one paper, return it
    if len(papers) == 1:
        return papers[0].get('id')
        
    c_start = chunk_info['page_start']
    c_end = chunk_info['page_end']
    
    best_paper = None
    max_overlap = 0
    
    for p in papers:
        p_start = p.get('start_page_estimate')
        if p_start is None: p_start = 0
            
        p_end = p.get('end_page_estimate')
        if p_end is None: p_end = 9999
        
        # Calculate overlap
        overlap_start = max(c_start, p_start)
        overlap_end = min(c_end, p_end)
        
        if overlap_start <= overlap_end:
            overlap_len = overlap_end - overlap_start + 1
            if overlap_len > max_overlap:
                max_overlap = overlap_len
                best_paper = p
    
    return best_paper.get('id') if best_paper else None
