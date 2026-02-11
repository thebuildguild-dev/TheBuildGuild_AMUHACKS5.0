"""
Embedder Module
Wraps Google Gemini API for embeddings and text generation
"""
import os
import time
from typing import List, Dict, Any, Optional
from functools import wraps
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
_client = None

def get_client() -> genai.Client:
    """Get or create Gemini client instance"""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _client = genai.Client(api_key=api_key)
        print("Gemini client initialized")
    return _client


# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_CALLS = []


def rate_limit(max_calls: int = RATE_LIMIT_REQUESTS_PER_MINUTE, period: int = 60):
    """
    Rate limiting decorator
    
    Args:
        max_calls: Maximum calls allowed per period
        period: Time period in seconds (default: 60)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global RATE_LIMIT_CALLS
            now = time.time()
            
            # Remove calls outside the current period
            RATE_LIMIT_CALLS = [call_time for call_time in RATE_LIMIT_CALLS if now - call_time < period]
            
            # Check if rate limit exceeded
            if len(RATE_LIMIT_CALLS) >= max_calls:
                sleep_time = period - (now - RATE_LIMIT_CALLS[0])
                if sleep_time > 0:
                    print(f"Rate limit reached, sleeping for {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    RATE_LIMIT_CALLS = []
            
            # Record this call
            RATE_LIMIT_CALLS.append(time.time())
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        print(f" All {max_retries} retry attempts failed")
                        raise
                    
                    # Check if it's a retryable error
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "quota" in error_msg or "429" in error_msg:
                        print(f"Rate limit error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    elif "timeout" in error_msg or "connection" in error_msg:
                        print(f"Connection error, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    else:
                        # Non-retryable error
                        raise
                    
                    time.sleep(delay)
                    delay *= backoff_factor
            
            raise last_exception
        return wrapper
    return decorator


@retry_with_backoff(max_retries=3)
@rate_limit(max_calls=50, period=60)
def embed_texts(texts: List[str], model: str = "gemini-embedding-001") -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Gemini
    
    Args:
        texts: List of text strings to embed
        model: Embedding model name (default: gemini-embedding-001)
    
    Returns:
        List of embedding vectors (list of floats)
    
    Raises:
        ValueError: If texts list is empty
        Exception: If API call fails
    """
    if not texts:
        raise ValueError("texts list cannot be empty")
    
    # Filter out empty strings
    texts = [text for text in texts if text and text.strip()]
    
    if not texts:
        raise ValueError("All texts are empty")
    
    try:
        client = get_client()
        
        # Call Gemini embedding API
        result = client.models.embed_content(
            model=model,
            contents=texts
        )
        
        # Extract embeddings from result
        embeddings = []
        if hasattr(result, 'embeddings'):
            embeddings = [embedding.values for embedding in result.embeddings]
        else:
            # Fallback: assume result is a list-like structure
            embeddings = list(result)
        
        print(f"Generated {len(embeddings)} embeddings (dim: {len(embeddings[0]) if embeddings else 0})")
        
        return embeddings
    
    except Exception as e:
        print(f" Error generating embeddings: {e}")
        raise


def embed_query(query: str, model: str = "gemini-embedding-001") -> List[float]:
    """
    Generate embedding for a single query string
    
    Args:
        query: Query text to embed
        model: Embedding model name
    
    Returns:
        Embedding vector (list of floats)
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    embeddings = embed_texts([query], model=model)
    return embeddings[0]


@retry_with_backoff(max_retries=3)
@rate_limit(max_calls=30, period=60)
def generate_text(
    prompt: str,
    model: str = "gemini-3-flash-preview",
    max_output_tokens: int = 2048,
    temperature: float = 0.7
) -> str:
    """
    Generate text using Gemini LLM
    
    Args:
        prompt: Input prompt text
        model: Model name (default: gemini-3-flash-preview)
        max_output_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
    
    Returns:
        Generated text string
    
    Raises:
        ValueError: If prompt is empty
        Exception: If API call fails
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    try:
        client = get_client()
        
        # Call Gemini generation API
        result = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            }
        )
        
        # Extract text from result
        if hasattr(result, 'text'):
            generated_text = result.text
        elif hasattr(result, 'candidates') and result.candidates:
            generated_text = result.candidates[0].content.parts[0].text
        else:
            generated_text = str(result)
        
        print(f"Generated {len(generated_text)} characters")
        
        return generated_text.strip()
    
    except Exception as e:
        print(f" Error generating text: {e}")
        raise


def analyze_with_gemini(
    subject: str,
    query: str,
    results: List[Any],
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Analyze PYQ results using Gemini to extract insights
    
    Args:
        subject: Subject name
        query: Original query
        results: List of QueryResult objects from search
        max_results: Maximum results to analyze
    
    Returns:
        Dictionary with analysis including topics, frequency, strategies
    """
    if not results:
        return {
            "topics": [],
            "insights": "No results to analyze",
            "recommendations": []
        }
    
    # Prepare context from results
    context_parts = []
    for idx, result in enumerate(results[:max_results]):
        context_parts.append(
            f"[Question {idx + 1}]\n"
            f"Text: {result.text[:300]}...\n"
            f"Year: {result.metadata.get('year', 'Unknown')}\n"
            f"Topic: {result.metadata.get('topic', 'Unknown')}\n"
            f"Marks: {result.metadata.get('marks', 'Unknown')}\n"
        )
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""Analyze these past year exam questions for {subject} related to: "{query}"

{context}

Provide a structured analysis in the following format:

1. Top 5 Topics (by frequency):
   - List topics that appear most frequently
   - Estimate how many times each appears
   - Estimate average marks allocation

2. Key Insights:
   - Difficulty patterns
   - Common question types
   - Important concepts

3. Study Recommendations:
   - Priority areas to focus on
   - Suggested preparation strategies
   - Time allocation suggestions

Keep the response concise and actionable."""

    try:
        analysis_text = generate_text(prompt, temperature=0.3)
        
        # Parse the response (simple parsing)
        analysis = {
            "raw_analysis": analysis_text,
            "topics": extract_topics_from_analysis(analysis_text),
            "insights": analysis_text,
            "recommendations": extract_recommendations(analysis_text),
        }
        
        return analysis
    
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
        return {
            "topics": [],
            "insights": f"Analysis failed: {str(e)}",
            "recommendations": []
        }


def extract_topics_from_analysis(text: str) -> List[Dict[str, Any]]:
    """
    Extract structured topic information from analysis text
    Simple heuristic-based extraction
    """
    topics = []
    lines = text.split('\n')
    
    in_topic_section = False
    for line in lines:
        if 'topic' in line.lower() and ':' in line:
            in_topic_section = True
            continue
        
        if in_topic_section and line.strip().startswith('-'):
            # Extract topic name (rough heuristic)
            topic_text = line.strip('- ').split(':')[0].split('(')[0].strip()
            if topic_text and len(topics) < 10:
                topics.append({
                    "name": topic_text,
                    "frequency": "high",  # Placeholder
                    "importance": "high"  # Placeholder
                })
        
        if in_topic_section and (line.strip().startswith('##') or 'insight' in line.lower()):
            break
    
    return topics


def extract_recommendations(text: str) -> List[str]:
    """Extract recommendations from analysis text"""
    recommendations = []
    lines = text.split('\n')
    
    in_recommendations = False
    for line in lines:
        if 'recommendation' in line.lower() or 'strategy' in line.lower():
            in_recommendations = True
            continue
        
        if in_recommendations and line.strip().startswith('-'):
            rec = line.strip('- ').strip()
            if rec:
                recommendations.append(rec)
    
    return recommendations[:5]  # Top 5 recommendations
