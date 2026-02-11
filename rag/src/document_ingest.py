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
from src.document_processor import process_document, extract_text_with_gemini
from src.embedder import embed_texts
from src.qdrant_client import ensure_collection
from qdrant_client.models import PointStruct

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
        
        # Insert document
        cur.execute(
            """
            INSERT INTO documents (sha256_hash, original_filename, total_pages, upload_source, source_url, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sha256_hash) DO NOTHING
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
        doc_id = result['id'] if result else None
        
        cur.close()
        conn.close()
        
        print(f"Saved document metadata: {doc_info['sha256'][:8]}...")
        return doc_id
    
    except Exception as e:
        print(f"Database save error: {e}")
        raise


async def save_chunk_metadata(doc_sha256: str, chunk_info: Dict, qdrant_id: str, text_content: str):
    """Save document chunk metadata to PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            INSERT INTO document_chunks 
            (document_sha256, chunk_number, page_range_start, page_range_end, qdrant_point_id, text_content)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_sha256, chunk_number) DO NOTHING
            """,
            (
                doc_sha256,
                chunk_info['chunk_number'],
                chunk_info['page_start'],
                chunk_info['page_end'],
                qdrant_id,
                text_content[:5000]  # Store first 5000 chars
            )
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
                
                # Track successful chunk uploads
                successful_chunks = []
                
                for chunk in doc_info['chunks']:
                    # Extract text with Gemini
                    text_content = extract_text_with_gemini(chunk['path'], chunk)
                    
                    if not text_content or len(text_content) < 50:
                        print(f"Skipping chunk {chunk['chunk_number']} - insufficient text")
                        continue
                    
                    # Generate embedding
                    embeddings = embed_texts([text_content])
                    embedding_vector = embeddings[0]
                    
                    # Create Qdrant point
                    point_id = str(uuid.uuid4())
                    
                    point = PointStruct(
                        id=point_id,
                        vector=embedding_vector,
                        payload={
                            "text": text_content,
                            "document_sha256": doc_info['sha256'],
                            "chunk_number": chunk['chunk_number'],
                            "page_range": f"{chunk['page_start']}-{chunk['page_end']}",
                            "original_filename": doc_info['original_filename'],
                            "total_pages": doc_info['total_pages'],
                        }
                    )
                    
                    # Upload to Qdrant
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=[point]
                    )
                    
                    print(f"Chunk {chunk['chunk_number']} uploaded to Qdrant")
                    
                    # Store chunk info for PostgreSQL save later
                    successful_chunks.append({
                        'chunk_info': chunk,
                        'point_id': point_id,
                        'text_content': text_content
                    })
                
                # Only save to PostgreSQL if at least one chunk was successful
                if successful_chunks:
                    # Save document metadata first
                    await save_document_metadata(doc_info, user_id)
                    
                    # Then save chunk metadata
                    for chunk_data in successful_chunks:
                        await save_chunk_metadata(
                            doc_info['sha256'],
                            chunk_data['chunk_info'],
                            chunk_data['point_id'],
                            chunk_data['text_content']
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
