"""Document service — business logic for knowledge base management.

Extracted from documents.py endpoint to separate concerns:
- API layer: validation, HTTP, response formatting
- Service layer: parsing, chunking, embedding, storage
"""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentChunk
from app.retrieval.document_parser import DocumentParser
from app.retrieval.chunker import TextChunker
from app.retrieval.embedder import get_embedding_service
from app.retrieval.vector_store import VectorStoreService
from app.core.config import get_settings

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt", ".text"}


class DocumentService:
    """Handles document upload, processing, and deletion."""

    @staticmethod
    async def process_upload(
        file_content: bytes,
        filename: str,
        session: AsyncSession,
    ) -> Document:
        """Upload and process a document.

        Parses, chunks, embeds, and stores in both SQLite and ChromaDB.
        """
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(f"不支持的文件类型: {suffix}")

        # Save file to disk
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}{suffix}"
        file_path.write_bytes(file_content)

        # Create document record
        doc = Document(
            id=file_id,
            user_id="default_user",
            title=filename,
            file_path=str(file_path),
            file_type=suffix.lstrip("."),
            file_size_bytes=len(file_content),
            status="processing",
        )
        session.add(doc)
        await session.flush()

        try:
            # Parse
            parser = DocumentParser()
            parsed = parser.parse(str(file_path))

            # Chunk
            settings = get_settings()
            chunker = TextChunker(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            chunks = chunker.chunk_document(parsed)

            # Embed
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
                        "source_file": filename,
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

    @staticmethod
    async def delete_document(document_id: str, session: AsyncSession) -> None:
        """Delete a document, its chunks, and vector embeddings."""
        result = await session.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError("文档未找到")

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

    @staticmethod
    async def list_documents(session: AsyncSession) -> list[Document]:
        """List all documents ordered by creation date."""
        result = await session.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_document(document_id: str, session: AsyncSession) -> Document | None:
        """Get a document by ID."""
        result = await session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_chunks(document_id: str, session: AsyncSession) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        result = await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())
