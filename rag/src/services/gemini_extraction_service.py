from typing import Any, Dict, Optional
import os
import time
import random
from src.clients.gemini_client import get_gemini_client, generate_content_with_retry
from google.genai import types

def extract_text_from_chunk(file_path: str, chunk_info: Dict[str, Any]) -> str:
    """
    Extract structured text from a PDF chunk using Gemini.
    """
    try:
        with open(file_path, "rb") as f:
            pdf_data = f.read()

        prompt = """Extract ALL text from this PDF exactly as it appears. 

Rules:
- Output ONLY the actual text content from the PDF
- Convert math equations to LaTeX: inline $...$ or display $$...$$
- Preserve question numbers, sections, and option labels (A, B, C, D)
- Do NOT add any annotations, descriptions, or metadata
- Do NOT add phrases like "Screenshot", "Continued from", or any other commentary
- Just extract the raw text content

Extract the text:"""
        response = generate_content_with_retry(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type='application/pdf'),
                prompt
            ]
        )
        return response.text if response and response.text else ""
        
    except Exception as e:
        print(f"Extraction failed for {file_path}: {e}")
        return ""
