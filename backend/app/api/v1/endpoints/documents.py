"""Document management endpoints for knowledge base."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse, DocumentListResponse, ChunkResponse
from app.retrieval.document_parser import DocumentParser
from app.retrieval.chunker import TextChunker
from app.retrieval.embedder import get_embedding_service
from app.retrieval.vector_store import VectorStoreService
from app.core.config import get_settings

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a document (PDF, MD, TXT) to the knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".md", ".markdown", ".txt", ".text"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    # Save file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}{suffix}"
    content = await file.read()
    file_path.write_bytes(content)

    # Create document record
    doc = Document(
        id=file_id,
        user_id="default_user",  # MVP: single user
        title=file.filename,
        file_path=str(file_path),
        file_type=suffix.lstrip("."),
        file_size_bytes=len(content),
        status="processing",
    )
    session.add(doc)
    await session.flush()

    # Process document: parse -> chunk -> embed
    try:
        parser = DocumentParser()
        parsed = parser.parse(str(file_path))

        chunker = TextChunker(
            chunk_size=get_settings().CHUNK_SIZE,
            chunk_overlap=get_settings().CHUNK_OVERLAP,
        )
        chunks = chunker.chunk_document(parsed)

        # Generate embeddings
        embedder = get_embedding_service()
        texts = [c.content for c in chunks]
        embeddings = embedder.embed_texts(texts)

        # Store chunks in DB
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chunk_record = DocumentChunk(
                id=chunk_id,
                document_id=file_id,
                user_id="default_user",
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                embedding_id=f"{file_id}_{i}",
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
            session.add(chunk_record)
            chunk_ids.append(f"{file_id}_{i}")

        # Store embeddings in ChromaDB
        vector_store = VectorStoreService()
        vector_store.add_chunks(
            chunk_ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": file_id,
                    "user_id": "default_user",
                    "source_file": file.filename,
                    "section_title": chunks[i].section_title or "",
                    "page_number": chunks[i].page_number or 0,
                }
                for i in range(len(chunks))
            ],
        )

        doc.chunk_count = len(chunks)
        doc.status = "completed"

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)

    await session.commit()
    return doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    session: AsyncSession = Depends(get_async_session),
):
    """List all uploaded documents."""
    result = await session.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific document."""
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")
    return doc


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get all chunks for a document."""
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
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
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")

    # Delete from vector store
    vector_store = VectorStoreService()
    vector_store.delete_by_document(document_id)

    # Delete file
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    # Delete from DB (chunks cascade)
    await session.delete(doc)
    await session.commit()

    return {"status": "已删除", "document_id": document_id}
