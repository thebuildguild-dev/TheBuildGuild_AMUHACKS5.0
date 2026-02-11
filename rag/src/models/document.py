from typing import List, Optional
from pydantic import BaseModel, Field

class Document(BaseModel):
    sha256: str
    original_filename: str
    total_pages: int
    source_type: str
    source_value: Optional[str] = None
    chunks: List[dict] = Field(default_factory=list)
    status: str = "pending"
