from typing import List, Dict

def map_page_to_chunk(page_number: int, chunks: List[Dict[str, any]]) -> int:
    """
    Find which chunk a page number belongs to.
    Returns the chunk number (1-based index)
    """
    for chunk in chunks:
        if chunk['page_start'] <= page_number <= chunk['page_end']:
            return chunk['chunk_number']
    return -1
