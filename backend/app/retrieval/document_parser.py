"""Document parser for PDF, Markdown, and TXT files."""

from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import DocumentProcessingError


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""

    title: str
    content: str
    file_type: str
    file_path: str
    file_size_bytes: int
    pages: list[dict] | None = None  # For PDF: [{page_number, content}]
    sections: list[dict] | None = None  # [{title, content, start_char}]


class DocumentParser:
    """Parses documents into structured text for chunking."""

    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a document file and return structured content."""
        path = Path(file_path)
        if not path.is_file():
            raise DocumentProcessingError(file_path, "File not found")

        suffix = path.suffix.lower()
        file_size = path.stat().st_size

        if suffix == ".pdf":
            return self._parse_pdf(path, file_size)
        elif suffix in (".md", ".markdown"):
            return self._parse_markdown(path, file_size)
        elif suffix in (".txt", ".text"):
            return self._parse_txt(path, file_size)
        else:
            raise DocumentProcessingError(
                file_path, f"Unsupported file type: {suffix}"
            )

    def _parse_pdf(self, path: Path, file_size: int) -> ParsedDocument:
        """Parse a PDF file using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise DocumentProcessingError(
                str(path), "PyMuPDF is required for PDF parsing. Install with: pip install pymupdf"
            )

        try:
            doc = fitz.open(str(path))
            pages = []
            full_content_parts = []

            for i, page in enumerate(doc):
                page_text = page.get_text("text")
                pages.append({"page_number": i + 1, "content": page_text})
                full_content_parts.append(page_text)

            doc.close()

            full_content = "\n\n".join(full_content_parts)

            return ParsedDocument(
                title=path.stem,
                content=full_content,
                file_type="pdf",
                file_path=str(path),
                file_size_bytes=file_size,
                pages=pages,
            )
        except Exception as e:
            raise DocumentProcessingError(str(path), str(e))

    def _parse_markdown(self, path: Path, file_size: int) -> ParsedDocument:
        """Parse a Markdown file, extracting sections."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="gbk")

        sections = self._extract_markdown_sections(content)

        return ParsedDocument(
            title=self._extract_title(content, path.stem),
            content=content,
            file_type="md",
            file_path=str(path),
            file_size_bytes=file_size,
            sections=sections,
        )

    def _parse_txt(self, path: Path, file_size: int) -> ParsedDocument:
        """Parse a plain text file."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="gbk")

        return ParsedDocument(
            title=path.stem,
            content=content,
            file_type="txt",
            file_path=str(path),
            file_size_bytes=file_size,
        )

    @staticmethod
    def _extract_markdown_sections(content: str) -> list[dict]:
        """Extract section headers and their content from markdown."""
        import re

        sections = []
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        matches = list(header_pattern.finditer(content))

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

            sections.append({
                "title": title,
                "level": level,
                "content": content[start:end].strip(),
                "start_char": start,
            })

        return sections

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        """Extract title from first heading or first line."""
        import re

        match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        first_line = content.strip().split("\n")[0].strip()
        return first_line[:200] if first_line else fallback
