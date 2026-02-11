import os
import PyPDF2
from typing import Optional

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
            if page_count > 0:
                _ = pdf_reader.pages[0].extract_text()
            
            print(f"Valid PDF: {page_count} pages")
            return page_count
    
    except Exception as e:
        print(f"PDF validation failed: {e}")
        return None
