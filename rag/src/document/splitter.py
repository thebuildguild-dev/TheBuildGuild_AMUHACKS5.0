import os
import PyPDF2
from typing import List, Dict
from pathlib import Path

PAGES_PER_CHUNK = 8  # Split PDFs into 8-page chunks

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
