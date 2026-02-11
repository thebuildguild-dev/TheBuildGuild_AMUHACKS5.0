"""
Document processor for handling PDF uploads, downloads, splitting, and text extraction
"""
import os
import uuid
import hashlib
import tempfile
import shutil
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import PyPDF2
from google import genai
from src.embedder import embed_texts, get_client

# Gemini client will be obtained from embedder module

PAGES_PER_CHUNK = 8  # Split PDFs into 8-page chunks


def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in 4KB chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def download_pdf(url: str, output_dir: str) -> Optional[Tuple[str, str]]:
    """
    Download PDF from URL
    Returns: (file_path, original_filename) or None if failed
    """
    try:
        print(f"Downloading PDF from {url}")
        response = requests.get(url, timeout=60, stream=True, verify=False)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
            print(f"Invalid content type: {content_type}")
            return None
        
        # Extract filename from URL or generate one
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(url)
        filename = unquote(os.path.basename(parsed_url.path))
        
        if not filename or not filename.endswith('.pdf'):
            filename = f"download_{uuid.uuid4().hex[:8]}.pdf"
        
        # Save to temp directory
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")
        return file_path, filename
    
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None


def validate_pdf(file_path: str) -> Optional[int]:
    """
    Validate PDF file and return page count
    Returns: page_count or None if invalid/corrupted
    """
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)
            
            # Try reading first page to ensure it's not corrupted
            _ = pdf_reader.pages[0].extract_text()
            
            print(f"Valid PDF: {page_count} pages")
            return page_count
    
    except Exception as e:
        print(f"PDF validation failed: {e}")
        return None


def split_pdf(file_path: str, output_dir: str, pages_per_chunk: int = PAGES_PER_CHUNK) -> List[Dict[str, any]]:
    """
    Split PDF into chunks of specified pages
    Returns: List of dicts with {path, chunk_number, page_start, page_end}
    """
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            if total_pages <= pages_per_chunk:
                # No splitting needed
                return [{
                    'path': file_path,
                    'chunk_number': 1,
                    'page_start': 1,
                    'page_end': total_pages,
                }]
            
            # Split into chunks
            chunks = []
            base_name = Path(file_path).stem
            
            chunk_number = 1
            for start_page in range(0, total_pages, pages_per_chunk):
                end_page = min(start_page + pages_per_chunk, total_pages)
                
                # Create new PDF for this chunk
                pdf_writer = PyPDF2.PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Save chunk
                chunk_filename = f"{base_name}-part{chunk_number}.pdf"
                chunk_path = os.path.join(output_dir, chunk_filename)
                
                with open(chunk_path, 'wb') as chunk_f:
                    pdf_writer.write(chunk_f)
                
                chunks.append({
                    'path': chunk_path,
                    'chunk_number': chunk_number,
                    'page_start': start_page + 1,  # 1-indexed
                    'page_end': end_page,
                })
                
                print(f"Created chunk {chunk_number}: pages {start_page + 1}-{end_page}")
                chunk_number += 1
            
            return chunks
    
    except Exception as e:
        print(f"PDF splitting failed: {e}")
        raise


def extract_text_with_gemini(pdf_path: str, chunk_info: Dict[str, any]) -> str:
    """
    Extract text from PDF chunk using Gemini Flash
    Converts math to LaTeX and maintains structure
    """
    try:
        print(f"Extracting text from {Path(pdf_path).name} using Gemini Flash...")
        
        client = get_client()
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Create prompt
        prompt = """Extract ALL text from this PDF exactly as it appears. 

Rules:
- Output ONLY the actual text content from the PDF
- Convert math equations to LaTeX: inline $...$ or display $$...$$
- Preserve question numbers, sections, and option labels (A, B, C, D)
- Do NOT add any annotations, descriptions, or metadata
- Do NOT add phrases like "Screenshot", "Continued from", or any other commentary
- Just extract the raw text content

Extract the text:"""
        
        # Use Gemini Flash for extraction with PDF data
        from google.genai import types
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                prompt
            ]
        )
        
        extracted_text = response.text
        print(f"Extracted {len(extracted_text)} characters")
        
        return extracted_text
    
    except Exception as e:
        print(f"Gemini extraction failed: {e}")
        # Fallback to simple extraction
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                print(f"Using fallback extraction: {len(text)} characters")
                return text
        except Exception as fallback_error:
            print(f"Fallback extraction also failed: {fallback_error}")
            return ""


def process_document(
    source: Dict[str, any],
    user_id: str,
    work_dir: str
) -> Optional[Dict[str, any]]:
    """
    Process a single document (URL or file buffer)
    
    Args:
        source: Dict with 'type' ('url' or 'file'), 'value' (url string or file buffer), 'filename'
        user_id: Firebase user ID
        work_dir: Working directory for temp files
    
    Returns:
        Dict with processing results or None if failed
    """
    try:
        # Download or save file
        if source['type'] == 'url':
            result = download_pdf(source['value'], work_dir)
            if not result:
                return {'error': 'Download failed', 'source': source['value']}
            file_path, original_filename = result
        else:
            # File buffer
            original_filename = source['filename']
            file_path = os.path.join(work_dir, original_filename)
            with open(file_path, 'wb') as f:
                f.write(source['value'])
            print(f"Saved uploaded file: {original_filename}")
        
        # Validate PDF
        total_pages = validate_pdf(file_path)
        if total_pages is None:
            return {'error': 'Invalid or corrupted PDF', 'filename': original_filename}
        
        # Compute SHA256
        sha256_hash = compute_sha256(file_path)
        print(f"SHA256: {sha256_hash}")
        
        # Split PDF if needed
        chunks = split_pdf(file_path, work_dir)
        print(f"Split into {len(chunks)} chunk(s)")
        
        return {
            'sha256': sha256_hash,
            'original_filename': original_filename,
            'total_pages': total_pages,
            'chunks': chunks,
            'file_path': file_path,
            'source_type': source['type'],
            'source_value': source.get('value') if source['type'] == 'url' else None,
        }
    
    except Exception as e:
        print(f"Document processing failed: {e}")
        return {'error': str(e), 'filename': source.get('filename', 'unknown')}
