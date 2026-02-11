import os
import uuid
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional, List, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get PostgreSQL connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set, DB features disabled")
        return None
    try:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"DB Connection failed: {e}")
        return None

def create_job(user_id: str, total_sources: int) -> str:
    """Create a new ingestion job in PostgreSQL"""
    conn = get_db_connection()
    job_id = str(uuid.uuid4())
    
    if not conn:
        return job_id
    
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ingestion_jobs 
            (job_id, user_id, status, total_sources, processed, successful, failed, duplicates, errors, documents)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (job_id, user_id, 'processing', total_sources, 0, 0, 0, 0, json.dumps([]), json.dumps([]))
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to create job in DB: {e}")
    finally:
        conn.close()
    
    return job_id

def update_job_status(job_id: str, updates: Dict):
    """Update job status in PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['errors', 'documents']:
                set_clauses.append(f"{key} = %s")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = %s")
                values.append(value)
        
        if set_clauses:
            values.append(job_id)
            query = f"UPDATE ingestion_jobs SET {', '.join(set_clauses)} WHERE job_id = %s"
            cur.execute(query, values)
            conn.commit()
    except Exception as e:
        print(f"Failed to update job status: {e}")
    finally:
        conn.close()

def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status from PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ingestion_jobs WHERE job_id = %s", (job_id,))
        result = cur.fetchone()
        
        if result:
            job_data = dict(result)
            job_data['created_at'] = job_data['created_at'].isoformat() if job_data.get('created_at') else None
            job_data['updated_at'] = job_data['updated_at'].isoformat() if job_data.get('updated_at') else None
            return job_data
        return None
    except Exception as e:
        print(f"Failed to get job status: {e}")
        return None
    finally:
        conn.close()

def check_document_exists(sha256_hash: str) -> Optional[Dict]:
    """Check if document already exists in database"""
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM documents WHERE sha256_hash = %s", (sha256_hash,))
        result = cur.fetchone()
        return dict(result) if result else None
    except Exception as e:
        print(f"Database check error: {e}")
        return None
    finally:
        conn.close()

def link_document_to_user(user_id: str, sha256_hash: str):
    """Link existing document to user"""
    conn = get_db_connection()
    if not conn: return

    try:
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
        print(f"Linked document {sha256_hash[:8]}... to user {user_id}")
    except Exception as e:
        print(f"Database link error: {e}")
    finally:
        conn.close()

def save_document_metadata(doc_info: Dict, user_id: str) -> Optional[str]:
    """Save document metadata to PostgreSQL"""
    conn = get_db_connection()
    if not conn: return None

    try:
        cur = conn.cursor()
        print(f"Saving metadata for SHA: {doc_info['sha256']}")

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
                doc_info.get('source_type', 'unknown'),
                doc_info.get('source_value'),
                'completed'
            )
        )
        result = cur.fetchone()
        chunk_db_id = result['id'] if result else None
        
        cur.execute(
            """
            INSERT INTO user_documents (user_id, document_sha256)
            VALUES (%s, %s)
            ON CONFLICT (user_id, document_sha256) DO NOTHING
            """,
            (user_id, doc_info['sha256'])
        )
        conn.commit()
        return chunk_db_id
    except Exception as e:
        print(f"Database save error: {e}")
        return None
    finally:
        conn.close()

def save_papers(doc_sha256: str, paper_list: List[Dict]) -> List[str]:
    """Save paper metadata and return IDs"""
    conn = get_db_connection()
    if not conn: return []

    paper_ids = []
    try:
        cur = conn.cursor()
        for paper in paper_list:
            year_val = str(paper.get('year')) if paper.get('year') is not None else None
            
            cur.execute(
                """
                SELECT id FROM papers 
                WHERE subject = %s AND year = %s AND exam_type = %s
                """,
                (paper.get('subject'), year_val, paper.get('exam_type'))
            )
            res = cur.fetchone()
            
            p_id = None
            if res:
                p_id = res['id']
            else:
                cur.execute(
                    """
                    INSERT INTO papers (document_sha256, subject, year, semester, paper_code, exam_type, difficulty, topics, start_page, end_page)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        doc_sha256,
                        paper.get('subject'), 
                        year_val, 
                        paper.get('semester'),
                        paper.get('paper_code'), 
                        paper.get('exam_type'),
                        paper.get('difficulty'),
                        json.dumps(paper.get('topics', [])),
                        paper.get('start_page'),
                        paper.get('end_page')
                    )
                )
                res_insert = cur.fetchone()
                if res_insert:
                  p_id = res_insert['id']

            if p_id:
                paper_ids.append(p_id)

        conn.commit()
        return paper_ids
    except Exception as e:
        print(f"Paper save error: {e}")
        return []
    finally:
        conn.close()

def save_chunk_metadata(doc_sha256: str, chunk_info: Dict, qdrant_id: str, text_content: str, paper_ids: List[str]):
    """Save chunk metadata and link papers"""
    conn = get_db_connection()
    if not conn: return

    try:
        cur = conn.cursor()
        
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
                chunk_info.get('page_start', 0),
                chunk_info.get('page_end', 0),
                qdrant_id,
                text_content[:5000] if text_content else ""
            )
        )
        
        result = cur.fetchone()
        chunk_db_id = result['id'] if result else None
        
        if not chunk_db_id:
             cur.execute("SELECT id FROM document_chunks WHERE document_sha256 = %s AND chunk_number = %s", 
                        (doc_sha256, chunk_info['chunk_number']))
             res = cur.fetchone()
             chunk_db_id = res['id'] if res else None

        if chunk_db_id:
            # Note: Previously we linked chunk_papers here. 
            # With the new design, paper metadata is stored in Qdrant payload directly.
            # We skip SQL relations for simpler RAG architecture.
            pass

        conn.commit()
    except Exception as e:
        print(f"Chunk metadata save error: {e}")
    finally:
        conn.close()
