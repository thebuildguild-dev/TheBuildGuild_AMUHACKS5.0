from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Chunk(BaseModel):
    document_sha256: str
    chunk_number: int
    page_start: int
    page_end: int
    text_content: Optional[str] = None
    qdrant_point_id: Optional[str] = None
    paper_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
