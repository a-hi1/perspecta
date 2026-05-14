"""Document-related API schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Request to create a new document."""
    title: str = Field(..., max_length=500)
    file_type: str = Field(..., pattern="^(pdf|md|txt)$")


class DocumentResponse(BaseModel):
    """Document response."""
    id: str
    title: str
    file_type: str
    file_size_bytes: int
    chunk_count: int
    status: str
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    """Document chunk response."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    source_file: str
    section_title: str | None = None
    page_number: int | None = None
    has_opinion: bool = False
    opinion_type: str | None = None
    opinion_text: str | None = None

    model_config = {"from_attributes": True}
