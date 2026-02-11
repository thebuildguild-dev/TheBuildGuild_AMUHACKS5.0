from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class PaperMetadata(BaseModel):
    subject: Optional[str] = None
    year: Optional[int] = None
    semester: Optional[str] = None
    paper_code: Optional[str] = None
    exam_type: Optional[str] = None # mid, final, etc.
    raw_analysis: Dict[str, Any] = Field(default_factory=dict)

class Paper(BaseModel):
    id: Optional[str] = None 
    metadata: PaperMetadata
    chunk_ids: list[str] = Field(default_factory=list)
