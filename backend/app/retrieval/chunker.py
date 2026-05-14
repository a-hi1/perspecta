"""Text chunking with overlap for RAG pipeline."""

from dataclasses import dataclass

from app.retrieval.document_parser import ParsedDocument


@dataclass
class TextChunk:
    """A chunk of text extracted from a document."""

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict | None = None


class TextChunker:
    """Splits document content into overlapping chunks.

    Supports two strategies:
    - Fixed-size: Split by character count with overlap
    - Section-aware: Split by markdown sections, then sub-chunk
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: ParsedDocument) -> list[TextChunk]:
        """Chunk a parsed document into text chunks."""
        if doc.file_type == "md" and doc.sections:
            return self._chunk_by_sections(doc)
        return self._chunk_fixed_size(doc)

    def _chunk_fixed_size(self, doc: ParsedDocument) -> list[TextChunk]:
        """Split text into fixed-size chunks with overlap."""
        text = doc.content
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to break at sentence boundary
            if end < len(text):
                boundary = self._find_sentence_boundary(text, end)
                if boundary > start + self.chunk_size // 2:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                # Determine page number if available
                page_num = self._find_page_number(doc, start) if doc.pages else None

                chunks.append(TextChunk(
                    content=chunk_text,
                    chunk_index=index,
                    start_char=start,
                    end_char=end,
                    page_number=page_num,
                ))
                index += 1

            start = end - self.chunk_overlap if end < len(text) else end

        return chunks

    def _chunk_by_sections(self, doc: ParsedDocument) -> list[TextChunk]:
        """Chunk by markdown sections, sub-chunking large sections."""
        chunks = []
        index = 0

        for section in doc.sections or []:
            section_text = section["content"]
            section_title = section["title"]

            if len(section_text) <= self.chunk_size:
                chunks.append(TextChunk(
                    content=section_text,
                    chunk_index=index,
                    start_char=section["start_char"],
                    end_char=section["start_char"] + len(section_text),
                    section_title=section_title,
                ))
                index += 1
            else:
                # Sub-chunk large sections
                sub_chunks = self._sub_chunk_text(section_text, section["start_char"])
                for sc in sub_chunks:
                    sc.chunk_index = index
                    sc.section_title = section_title
                    chunks.append(sc)
                    index += 1

        return chunks

    def _sub_chunk_text(self, text: str, base_offset: int) -> list[TextChunk]:
        """Sub-chunk a large text block."""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                boundary = self._find_sentence_boundary(text, end)
                if boundary > start + self.chunk_size // 2:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(TextChunk(
                    content=chunk_text,
                    chunk_index=0,
                    start_char=base_offset + start,
                    end_char=base_offset + end,
                ))

            start = end - self.chunk_overlap if end < len(text) else end

        return chunks

    @staticmethod
    def _find_sentence_boundary(text: str, position: int) -> int:
        """Find the nearest sentence boundary before the given position."""
        # Look for sentence-ending punctuation
        for i in range(position, max(position - 100, 0), -1):
            if text[i] in ".!?\n":
                return i + 1
        return position

    @staticmethod
    def _find_page_number(doc: ParsedDocument, char_position: int) -> int | None:
        """Find which page a character position falls in."""
        if not doc.pages:
            return None

        current_pos = 0
        for page in doc.pages:
            page_len = len(page["content"])
            if current_pos + page_len >= char_position:
                return page["page_number"]
            current_pos += page_len + 2  # +2 for the \n\n join

        return None
