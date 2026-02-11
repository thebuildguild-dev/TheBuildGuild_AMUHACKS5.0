"""
Ingestion Module
Orchestrates the PDF ingestion pipeline:
PDF -> Text -> Chunks -> Embeddings -> Qdrant
"""
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

from src.pdf_parser import extract_text_from_pdf, list_pdfs_in_folder
from src.text_splitter import chunk_texts
from src.embedder import embed_texts
from src.qdrant_client import (
    create_client,
    ensure_collection,
    upsert_vectors,
    get_collection_info
)
from src.course_info import analyze_pdf_content


def infer_subject_from_filename(filename: str) -> str:
    """
    Attempt to infer subject from filename
    
    Args:
        filename: PDF filename
    
    Returns:
        Inferred subject name or 'Unknown'
    """
    # Common subject patterns
    subject_patterns = {
        r'math|mathematics|calculus|algebra|geometry': 'Mathematics',
        r'phys|physics': 'Physics',
        r'chem|chemistry': 'Chemistry',
        r'bio|biology': 'Biology',
        r'cs|computer|programming|data\s*struct|algorithm': 'Computer Science',
        r'eng|english|literature': 'English',
        r'hist|history': 'History',
        r'geo|geography': 'Geography',
        r'econ|economics': 'Economics',
        r'account|accounting': 'Accounting',
        r'management|business': 'Management',
        r'electronics|ece': 'Electronics',
        r'mechanical|mech': 'Mechanical Engineering',
        r'civil': 'Civil Engineering',
        r'electrical|eee': 'Electrical Engineering',
    }
    
    filename_lower = filename.lower()
    
    for pattern, subject in subject_patterns.items():
        if re.search(pattern, filename_lower):
            return subject
    
    # Try to extract subject from common patterns like "Subject_2024.pdf"
    match = re.search(r'([a-zA-Z\s]+)[\-_]?\d{4}', filename)
    if match:
        potential_subject = match.group(1).strip().replace('_', ' ').replace('-', ' ')
        return potential_subject.title()
    
    return 'Unknown'


def ingest_year(
    year: str,
    folder_path: str,
    client: Any = None,
    collection_name: str = "amu_pyq",
    force: bool = False,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Ingest PDFs for a specific year into Qdrant
    
    Args:
        year: Academic year (e.g., '2024' or '2024-2025')
        folder_path: Path to folder containing PDF files
        client: QdrantClient instance (optional, will create if None)
        collection_name: Name of Qdrant collection
        force: Force re-ingestion even if already processed
        batch_size: Number of chunks to process in each embedding batch
    
    Returns:
        Summary dictionary with ingestion statistics
    """
    print(f"\n{'='*60}")
    print(f"Starting ingestion for year {year}")
    print(f"Source: {folder_path}")
    print(f"Collection: {collection_name}")
    print(f"{'='*60}\n")
    
    # Initialize summary
    summary = {
        'year': year,
        'folder_path': folder_path,
        'files_ingested': 0,
        'files_failed': 0,
        'total_chunks': 0,
        'vectors_upserted': 0,
        'errors': [],
    }
    
    try:
        # Create client if not provided
        if client is None:
            client = create_client()
        
        # Ensure collection exists
        ensure_collection(client, collection_name)
        
        # List all PDF files
        pdf_files = list(list_pdfs_in_folder(folder_path, recursive=True))
        
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return summary
        
        print(f"Found {len(pdf_files)} PDF files to process\n")
        
        # Process each PDF
        all_points = []
        
        for pdf_idx, pdf_path in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_path)
            print(f"\n[{pdf_idx}/{len(pdf_files)}] Processing: {filename}")
            
            try:
                # Extract text from PDF
                print(f"  → Extracting text...")
                text = extract_text_from_pdf(pdf_path)
                
                if not text or len(text.strip()) < 100:
                    print(f"  Skipping {filename}: insufficient text content")
                    summary['files_failed'] += 1
                    continue
                
                # AI-powered content analysis
                print(f"  → Analyzing content with AI...")
                content_analysis = analyze_pdf_content(text, filename, year)
                
                # Extract comprehensive course info (may have multiple courses per PDF)
                courses_info = content_analysis['courses_info']
                print(f"  → Found {len(courses_info)} course(s) in this PDF")
                
                # Sort courses by position for page-aware assignment
                courses_info_sorted = sorted(courses_info, key=lambda x: x.get('_position', 0))
                
                # Log extracted courses
                for idx, course in enumerate(courses_info_sorted):
                    title = course['subject_identity']['title']
                    code = course['subject_identity']['code']
                    pos = course.get('_position', 0)
                    conf = course.get('_confidence', 'unknown')
                    print(f"  → Course {idx+1}: {title} ({code}) at pos {pos} [{conf}]")
                
                # Use enhanced text with math markers
                text_to_chunk = content_analysis['enhanced_text']
                
                # Create chunks with position tracking
                print(f"  → Chunking text with position tracking...")
                from src.text_splitter import split_text_by_tokens
                chunk_texts_list = split_text_by_tokens(text_to_chunk)
                
                # Assign each chunk to the appropriate course based on its position
                chunks = []
                current_pos = 0
                
                for chunk_idx, chunk_text in enumerate(chunk_texts_list):
                    # Find chunk position in original text
                    chunk_start = text_to_chunk.find(chunk_text, current_pos)
                    if chunk_start == -1:
                        chunk_start = current_pos  # Fallback
                    chunk_end = chunk_start + len(chunk_text)
                    chunk_mid = (chunk_start + chunk_end) // 2  # Middle of chunk
                    current_pos = chunk_end
                    
                    # Determine which course this chunk belongs to
                    # Find the course whose position is before or at this chunk
                    assigned_course = courses_info_sorted[0]  # Default to first
                    for course in courses_info_sorted:
                        course_pos = course.get('_position', 0)
                        if course_pos <= chunk_mid:
                            assigned_course = course
                        else:
                            break  # Courses are sorted by position
                    
                    # Create metadata specific to this chunk's course
                    chunk_metadata = {
                        'year': year,
                        'source_filename': filename,
                        'file_path': pdf_path,
                        'chunk_index': chunk_idx,
                        'chunk_position': chunk_start,
                        
                        # Course identity for THIS chunk
                        'subject_title': assigned_course['subject_identity']['title'],
                        'course_code': assigned_course['subject_identity']['code'],
                        'department_code': assigned_course['subject_identity'].get('department_code', ''),
                        'is_cbc': assigned_course['subject_identity'].get('is_cbc', False),
                        
                        # Academic details for THIS chunk's course
                        'faculty': assigned_course['academic_details'].get('faculty', ''),
                        'offering_department': assigned_course['academic_details'].get('offering_department', ''),
                        'level': assigned_course['academic_details'].get('level', ''),
                        'applicable_programs': assigned_course['academic_details'].get('applicable_programs', []),
                        'branches': assigned_course['academic_details'].get('branches', []),
                        'semester': assigned_course['academic_details'].get('semester', 0),
                        'academic_year': assigned_course['academic_details'].get('year', 0),
                        'credits': assigned_course['academic_details'].get('credits', 0),
                        
                        # Store THIS course's syllabus and evaluation
                        'syllabus_units': json.dumps(assigned_course.get('syllabus_content', {})),
                        'evaluation_scheme': json.dumps(assigned_course.get('evaluation_scheme', {})),
                        
                        # Overall PDF context (all courses in this PDF)
                        'all_course_codes_in_pdf': [c['subject_identity']['code'] for c in courses_info],
                        'total_courses_in_pdf': len(courses_info),
                        
                        # Content detection (PDF-wide)
                        'has_math': content_analysis['has_math'],
                        'has_or_questions': len(content_analysis['or_questions']) > 0,
                        'or_question_count': len(content_analysis['or_questions']),
                        'has_figures': content_analysis['stats']['has_figures'],
                        'has_diagrams': content_analysis['stats']['has_diagrams'],
                    }
                    
                    # Generate unique ID for this chunk
                    from uuid import uuid4
                    chunk_id = str(uuid4())
                    
                    chunks.append({
                        'id': chunk_id,
                        'text': chunk_text,
                        'metadata': chunk_metadata
                    })
                
                if not chunks:
                    print(f"  No chunks created for {filename}")
                    summary['files_failed'] += 1
                    continue
                
                print(f"  → Created {len(chunks)} chunks with course-aware metadata")
                summary['total_chunks'] += len(chunks)
                
                # Process chunks in batches for embedding
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]
                    batch_texts = [chunk['text'] for chunk in batch]
                    
                    print(f"  → Generating embeddings for batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")
                    
                    try:
                        # Generate embeddings
                        embeddings = embed_texts(batch_texts)
                        
                        # Create points for Qdrant
                        for chunk, embedding in zip(batch, embeddings):
                            point = {
                                'id': chunk['id'],
                                'vector': embedding,
                                'payload': {
                                    'text': chunk['text'],
                                    **chunk['metadata']
                                }
                            }
                            all_points.append(point)
                    
                    except Exception as e:
                        print(f"   Error processing batch: {e}")
                        summary['errors'].append({
                            'file': filename,
                            'error': str(e),
                            'batch': i // batch_size + 1
                        })
                        continue
                
                summary['files_ingested'] += 1
                print(f"  Successfully processed {filename}")
            
            except Exception as e:
                print(f"   Error processing {filename}: {e}")
                summary['files_failed'] += 1
                summary['errors'].append({
                    'file': filename,
                    'error': str(e)
                })
                continue
        
        # Upsert all points to Qdrant
        if all_points:
            print(f"\n{'='*60}")
            print(f"Upserting {len(all_points)} vectors to Qdrant...")
            print(f"{'='*60}\n")
            
            try:
                vectors_upserted = upsert_vectors(
                    client=client,
                    collection_name=collection_name,
                    points=all_points,
                    batch_size=100
                )
                summary['vectors_upserted'] = vectors_upserted
                print(f"\nSuccessfully upserted {vectors_upserted} vectors")
            
            except Exception as e:
                print(f"\n Error upserting vectors: {e}")
                summary['errors'].append({
                    'stage': 'upsert',
                    'error': str(e)
                })
        
        # Get final collection info
        try:
            collection_info = get_collection_info(client, collection_name)
            print(f"\nCollection '{collection_name}' now has {collection_info['vectors_count']} vectors")
        except:
            pass
        
        # Print summary
        print(f"\n{'='*60}")
        print("Ingestion Summary")
        print(f"{'='*60}")
        print(f"Year: {summary['year']}")
        print(f"Files processed: {summary['files_ingested']}/{len(pdf_files)}")
        print(f"Files failed: {summary['files_failed']}")
        print(f"Total chunks: {summary['total_chunks']}")
        print(f"Vectors upserted: {summary['vectors_upserted']}")
        print(f"Errors: {len(summary['errors'])}")
        print(f"{'='*60}\n")
        
        return summary
    
    except Exception as e:
        print(f"\n Fatal error during ingestion: {e}")
        summary['errors'].append({
            'stage': 'fatal',
            'error': str(e)
        })
        raise


def ingest_multiple_years(
    years: List[str],
    base_path: str,
    collection_name: str = "amu_pyq",
    year_folder_pattern: str = "{year}"
) -> Dict[str, Any]:
    """
    Ingest multiple years of PDFs
    
    Args:
        years: List of year strings
        base_path: Base path containing year folders
        collection_name: Qdrant collection name
        year_folder_pattern: Pattern for year folder naming (use {year} placeholder)
    
    Returns:
        Aggregated summary across all years
    """
    client = create_client()
    ensure_collection(client, collection_name)
    
    aggregated_summary = {
        'total_years': len(years),
        'years_processed': 0,
        'total_files': 0,
        'total_chunks': 0,
        'total_vectors': 0,
        'year_summaries': {}
    }
    
    for year in years:
        folder_path = os.path.join(base_path, year_folder_pattern.format(year=year))
        
        if not os.path.exists(folder_path):
            print(f"Folder not found for year {year}: {folder_path}")
            continue
        
        try:
            summary = ingest_year(
                year=year,
                folder_path=folder_path,
                client=client,
                collection_name=collection_name
            )
            
            aggregated_summary['years_processed'] += 1
            aggregated_summary['total_files'] += summary['files_ingested']
            aggregated_summary['total_chunks'] += summary['total_chunks']
            aggregated_summary['total_vectors'] += summary['vectors_upserted']
            aggregated_summary['year_summaries'][year] = summary
        
        except Exception as e:
            print(f" Failed to ingest year {year}: {e}")
            continue
    
    return aggregated_summary


# CLI entrypoint
def main():
    """Command-line interface for ingestion"""
    parser = argparse.ArgumentParser(
        description="Ingest AMU PYQ PDFs into Qdrant vector database"
    )
    
    parser.add_argument(
        'command',
        choices=['ingest_year', 'ingest_multiple'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--year',
        type=str,
        help='Academic year (e.g., 2024 or 2024-2025)'
    )
    
    parser.add_argument(
        '--years',
        type=str,
        nargs='+',
        help='Multiple years to ingest'
    )
    
    parser.add_argument(
        '--path',
        type=str,
        required=True,
        help='Path to folder containing PDF files'
    )
    
    parser.add_argument(
        '--collection',
        type=str,
        default='amu_pyq',
        help='Qdrant collection name (default: amu_pyq)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-ingestion'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for embedding generation (default: 10)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'ingest_year':
            if not args.year:
                print(" Error: --year is required for ingest_year command")
                return 1
            
            summary = ingest_year(
                year=args.year,
                folder_path=args.path,
                collection_name=args.collection,
                force=args.force,
                batch_size=args.batch_size
            )
            
            print("\nIngestion completed successfully!")
            return 0
        
        elif args.command == 'ingest_multiple':
            if not args.years:
                print(" Error: --years is required for ingest_multiple command")
                return 1
            
            summary = ingest_multiple_years(
                years=args.years,
                base_path=args.path,
                collection_name=args.collection
            )
            
            print("\nMulti-year ingestion completed!")
            print(f"Processed {summary['years_processed']}/{summary['total_years']} years")
            print(f"Total vectors: {summary['total_vectors']}")
            return 0
    
    except Exception as e:
        print(f"\n Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
