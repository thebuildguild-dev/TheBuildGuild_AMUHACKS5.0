"""
Text Splitter Module
Splits long text into manageable chunks for embedding and storage
"""
import re
from typing import List, Dict, Any
from uuid import uuid4


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using simple heuristic
    Approximation: 1 token ≈ 4 characters on average
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    # Simple estimation: split on whitespace and count
    # More accurate than character count
    words = text.split()
    # Average: 1.3 tokens per word in English
    return int(len(words) * 1.3)


def split_text_by_tokens(
    text: str,
    target_tokens: int = 500,
    min_tokens: int = 400,
    max_tokens: int = 600,
    overlap_tokens: int = 50
) -> List[str]:
    """
    Split text into chunks based on token count
    
    Args:
        text: Input text to split
        target_tokens: Target tokens per chunk
        min_tokens: Minimum tokens per chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Split into sentences (preserve sentence boundaries)
    sentences = re.split(r'([.!?]\s+|\n{2,})', text)
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        separator = sentences[i + 1] if i + 1 < len(sentences) else ""
        
        sentence_tokens = estimate_tokens(sentence)
        
        # If single sentence is too large, split it by words
        if sentence_tokens > max_tokens:
            # Split oversized sentence
            words = sentence.split()
            word_chunk = []
            word_tokens = 0
            
            for word in words:
                word_token_estimate = estimate_tokens(word)
                
                if word_tokens + word_token_estimate > target_tokens and word_chunk:
                    chunks.append(' '.join(word_chunk))
                    # Keep overlap
                    overlap_words = word_chunk[-overlap_tokens:] if len(word_chunk) > overlap_tokens else word_chunk
                    word_chunk = overlap_words + [word]
                    word_tokens = estimate_tokens(' '.join(word_chunk))
                else:
                    word_chunk.append(word)
                    word_tokens += word_token_estimate
            
            if word_chunk:
                chunks.append(' '.join(word_chunk))
            
            continue
        
        # Check if adding this sentence exceeds max_tokens
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunks.append(''.join(current_chunk).strip())
            
            # Start new chunk with overlap
            overlap_text = ''.join(current_chunk[-3:])  # Last 3 sentences
            current_chunk = [overlap_text] if overlap_text else []
            current_tokens = estimate_tokens(overlap_text)
        
        current_chunk.append(sentence + separator)
        current_tokens += sentence_tokens
        
        # If we've reached target tokens and have minimum content, consider finishing chunk
        if current_tokens >= target_tokens and current_tokens <= max_tokens:
            chunks.append(''.join(current_chunk).strip())
            # Start new chunk with overlap
            overlap_text = ''.join(current_chunk[-2:])  # Last 2 sentences
            current_chunk = [overlap_text] if overlap_text else []
            current_tokens = estimate_tokens(overlap_text)
    
    # Add remaining text
    if current_chunk:
        remaining_text = ''.join(current_chunk).strip()
        if estimate_tokens(remaining_text) >= min_tokens or not chunks:
            chunks.append(remaining_text)
        elif chunks:
            # Too small, append to last chunk
            chunks[-1] += ' ' + remaining_text
    
    return [chunk for chunk in chunks if chunk.strip()]


def chunk_texts(
    text: str,
    metadata: Dict[str, Any],
    target_tokens: int = 500,
    min_tokens: int = 400,
    max_tokens: int = 600
) -> List[Dict[str, Any]]:
    """
    Split text into chunks with metadata
    
    Args:
        text: Input text to chunk
        metadata: Base metadata dict with keys like:
            - year: Academic year
            - subject: Subject name
            - source_filename: Original PDF filename
            - page_range: Page range (optional)
        target_tokens: Target tokens per chunk (default: 500)
        min_tokens: Minimum tokens per chunk (default: 400)
        max_tokens: Maximum tokens per chunk (default: 600)
    
    Returns:
        List of chunk dictionaries with structure:
        {
            'id': unique_id,
            'text': chunk_text,
            'metadata': {
                ...base_metadata,
                'chunk_id': chunk_index,
                'chunk_tokens': estimated_tokens,
                'total_chunks': total_count
            }
        }
    """
    if not text or not text.strip():
        print(f"Empty text provided for chunking")
        return []
    
    # Split text into chunks
    chunks = split_text_by_tokens(
        text,
        target_tokens=target_tokens,
        min_tokens=min_tokens,
        max_tokens=max_tokens
    )
    
    if not chunks:
        print(f"No chunks created from text")
        return []
    
    # Create chunk documents
    chunk_docs = []
    total_chunks = len(chunks)
    
    for idx, chunk_text in enumerate(chunks):
        chunk_tokens = estimate_tokens(chunk_text)
        
        chunk_doc = {
            'id': str(uuid4()),
            'text': chunk_text,
            'metadata': {
                **metadata,  # Base metadata
                'chunk_id': idx,
                'chunk_tokens': chunk_tokens,
                'total_chunks': total_chunks,
                'char_count': len(chunk_text),
            }
        }
        
        chunk_docs.append(chunk_doc)
    
    print(f"Created {total_chunks} chunks (avg {sum(estimate_tokens(c) for c in chunks) / total_chunks:.0f} tokens/chunk)")
    
    return chunk_docs


def chunk_by_sections(
    text: str,
    metadata: Dict[str, Any],
    section_pattern: str = r'\n#{1,3}\s+.*?\n|\n\d+\.\s+.*?\n'
) -> List[Dict[str, Any]]:
    """
    Split text by sections (headers, numbered items) instead of fixed token count
    Useful for structured documents like exams with questions
    
    Args:
        text: Input text
        metadata: Base metadata
        section_pattern: Regex pattern to identify section boundaries
    
    Returns:
        List of chunk dictionaries
    """
    # Split by section headers
    sections = re.split(section_pattern, text)
    sections = [s.strip() for s in sections if s.strip()]
    
    if not sections:
        # Fallback to token-based chunking
        return chunk_texts(text, metadata)
    
    chunk_docs = []
    
    for idx, section_text in enumerate(sections):
        tokens = estimate_tokens(section_text)
        
        # If section is too large, split it further
        if tokens > 600:
            sub_chunks = chunk_texts(
                section_text,
                {**metadata, 'section_id': idx}
            )
            chunk_docs.extend(sub_chunks)
        else:
            chunk_doc = {
                'id': str(uuid4()),
                'text': section_text,
                'metadata': {
                    **metadata,
                    'chunk_id': idx,
                    'chunk_tokens': tokens,
                    'total_chunks': len(sections),
                    'section_id': idx,
                }
            }
            chunk_docs.append(chunk_doc)
    
    return chunk_docs


def merge_small_chunks(
    chunks: List[Dict[str, Any]],
    min_tokens: int = 300
) -> List[Dict[str, Any]]:
    """
    Merge chunks that are too small
    
    Args:
        chunks: List of chunk documents
        min_tokens: Minimum tokens per chunk
    
    Returns:
        List of merged chunk documents
    """
    if not chunks:
        return []
    
    merged = []
    buffer = None
    
    for chunk in chunks:
        tokens = chunk['metadata'].get('chunk_tokens', 0)
        
        if tokens < min_tokens and buffer:
            # Merge with buffer
            buffer['text'] += '\n\n' + chunk['text']
            buffer['metadata']['chunk_tokens'] += tokens
            buffer['metadata']['char_count'] += chunk['metadata'].get('char_count', 0)
        elif tokens < min_tokens:
            # Start buffer
            buffer = chunk
        else:
            if buffer:
                merged.append(buffer)
                buffer = None
            merged.append(chunk)
    
    # Add remaining buffer
    if buffer:
        merged.append(buffer)
    
    return merged
