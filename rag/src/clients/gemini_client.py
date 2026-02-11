import os
import time
import random
from typing import Optional
from functools import wraps
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_gemini_client() -> genai.Client:
    """Get or create singleton Gemini client"""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _client = genai.Client(api_key=api_key)
    return _client

def generate_content_with_retry(
    model: str, 
    contents: list, 
    config: Optional[types.GenerateContentConfig] = None, 
    retries: int = 5, 
    initial_delay: float = 2.0
):
    """
    Call Gemini generate_content with exponential backoff for 503/429 errors.
    Wrapper around the client method.
    """
    client = get_gemini_client()
    delay = initial_delay
    
    for attempt in range(retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str:
                if attempt == retries - 1:
                    raise  # Re-raise on last attempt
                
                wait_time = delay + random.uniform(0, 1)
                print(f"Gemini API busy (503/429). Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{retries})")
                time.sleep(wait_time)
                delay *= 2  # Exponential backoff
            else:
                raise  # Re-raise other errors immediately
