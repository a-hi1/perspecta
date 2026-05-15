"""Document management endpoints for knowledge base."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.document import DocumentResponse, DocumentListResponse, ChunkResponse
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a document (PDF, MD, TXT) to the knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")

    content = await file.read()
    try:
        doc = await DocumentService.process_upload(content, file.filename, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    session: AsyncSession = Depends(get_async_session),
):
    """List all uploaded documents."""
    docs = await DocumentService.list_documents(session)
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific document."""
    doc = await DocumentService.get_document(document_id, session)
    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")
    return doc


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get all chunks for a document."""
    chunks = await DocumentService.get_chunks(document_id, session)
    return [
        ChunkResponse(
            id=c.id,
            document_id=c.document_id,
            content=c.content,
            chunk_index=c.chunk_index,
            source_file=document_id,
            section_title=c.section_title,
            page_number=c.page_number,
            has_opinion=c.has_opinion,
            opinion_type=c.opinion_type,
            opinion_text=c.opinion_text,
        )
        for c in chunks
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a document and its chunks."""
    try:
        await DocumentService.delete_document(document_id, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status": "已删除", "document_id": document_id}
