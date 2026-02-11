from typing import List, Dict, Any
import json
import re
from src.config import config
from src.clients.gemini_client import get_gemini_client, generate_content_with_retry
from google.genai import types

def detect_exam_papers(text_content: str) -> List[Dict[str, Any]]:
    """
    Analyze extracted text to identify exam papers and metadata.
    """
    if not text_content or len(text_content) < 50:
        return []

    prompt = """
    Analyze the following text which contains one or more exam papers.
    The text includes page markers like "--- PAGE START: X END: Y ---".
    
    Identify distinct exam papers and extract metadata for each, including their page range.
    
    Return a valid JSON array of objects with these fields:
    - subject: Subject name (e.g. Physics, Mathematics)
    - year: Year (integer, e.g. 2023)
    - semester: Semester (e.g. "Sem I", "Autumn")
    - paper_code: Course code if available (e.g. "PHYS101")
    - exam_type: Type (e.g. "Mid-Sem", "End-Sem", "Sessional")
    - start_page: The starting page number of this paper (integer)
    - end_page: The ending page number of this paper (integer)
    - topics: List of topics covered
    - difficulty: Estimated difficulty (Easy/Medium/Hard)
    
    If multiple papers are present, list them all. Ensure pages are accurate based on markers.
    """
    
    try:
        response = generate_content_with_retry(
            model=config.GEMINI_GENERATION_MODEL,
            contents=[prompt, text_content[:50000]],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        try:
             json_str = response.text
             if "```json" in json_str:
                 json_str = json_str.split("```json")[1].split("```")[0]
             elif "```" in json_str:
                 json_str = json_str.split("```")[1].split("```")[0]
                 
             return json.loads(json_str)
        except json.JSONDecodeError as e:
             print(f"Failed to parse JSON for metadata: {e}")
             print(f"Gemini response (first 500 chars): {response.text[:500]}")
             return []

    except Exception as e:
        print(f"Metadata detection failed: {e}")
        return []
