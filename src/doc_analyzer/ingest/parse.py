"""Document bytes → text. Pure functions, no Spark imports."""

from __future__ import annotations

import hashlib
import io
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import PurePosixPath

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HTML_MIME = "text/html"
MARKDOWN_MIME = "text/markdown"
TEXT_MIME = "text/plain"
UNKNOWN_MIME = "application/octet-stream"

_EXTENSIONS = {
    ".pdf": PDF_MIME,
    ".docx": DOCX_MIME,
    ".html": HTML_MIME,
    ".htm": HTML_MIME,
    ".md": MARKDOWN_MIME,
    ".markdown": MARKDOWN_MIME,
    ".txt": TEXT_MIME,
}
_MAGIC = {PDF_MIME: b"%PDF", DOCX_MIME: b"PK"}
_NON_VISIBLE_TAGS = ["head", "script", "style", "noscript", "template", "svg"]
_MARKDOWN_H1 = re.compile(r"^# +(.+?)\s*#*\s*$", re.MULTILINE)


class ParseError(Exception):
    """Raised when a document cannot be parsed; recorded as parse_status='error' in silver."""


@dataclass(frozen=True)
class Page:
    """Text of one page. Formats without real pages (DOCX, HTML, TXT, MD) produce one page 1."""

    page_number: int  # 1-indexed
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    """Result of parsing one file: its type, optional title and text split by page."""

    mime_type: str
    title: str | None
    pages: list[Page] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Full document text.

        Returns:
            The text of every page in page order, joined with a blank line ("\\n\\n").
            Empty string if the document has no pages.
        """
        return "\n\n".join(p.text for p in self.pages)


def compute_doc_id(content: bytes) -> str:
    """Content-addressed document id, so the same file uploaded twice gets the same id.

    Args:
        content: Raw file bytes.

    Returns:
        Lowercase sha256 hex digest of the bytes (64 characters).
    """
    return hashlib.sha256(content).hexdigest()


def detect_mime_type(path: str, content: bytes) -> str:
    """Detect the document type from its extension, confirmed by magic bytes where possible
    (PDF starts with b"%PDF", DOCX is a zip starting with b"PK").

    Args:
        path: Source path or file name; only the extension is used.
        content: Raw file bytes.

    Returns:
        One of "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/html", "text/markdown", "text/plain";
        or "application/octet-stream" if the type is unknown or unsupported.
    """
    suffix = PurePosixPath(path.replace("\\", "/")).suffix.lower()
    mime = _EXTENSIONS.get(suffix, UNKNOWN_MIME)
    magic = _MAGIC.get(mime)
    if magic is not None and not content.startswith(magic):
        return UNKNOWN_MIME
    return mime


def parse_document(path: str, content: bytes) -> ParsedDocument:
    """Parse any supported file: detect its type, then call the matching parser.

    Args:
        path: Source path or file name, used for type detection.
        content: Raw file bytes.

    Returns:
        The ParsedDocument from the matching parser.

    Raises:
        ParseError: If the type is unsupported, the parser fails, or no text could be
            extracted at all (e.g. a scanned PDF with no text layer). The original
            exception is chained as the cause.
    """
    mime = detect_mime_type(path, content)
    parser = _PARSERS.get(mime)
    if parser is None:
        raise ParseError(f"unsupported file type: {path}")

    try:
        doc = parser(content)
    except Exception as e:
        raise ParseError(f"failed to parse {path}: {e}") from e

    if mime == MARKDOWN_MIME:
        heading = _MARKDOWN_H1.search(doc.text)
        doc = replace(doc, mime_type=MARKDOWN_MIME, title=heading.group(1) if heading else None)

    if not doc.text.strip():
        raise ParseError(f"no text could be extracted from {path}")
    logger.debug("parsed %s as %s (%d pages)", path, mime, len(doc.pages))
    return doc


def parse_pdf(content: bytes) -> ParsedDocument:
    """Extract text per page from a PDF with pypdf.

    Args:
        content: Raw PDF bytes.

    Returns:
        ParsedDocument with mime_type "application/pdf", title from the PDF metadata
        (None if missing), and one Page per PDF page, numbered from 1. Pages with no
        extractable text are kept with empty text so page numbers stay correct.
    """
    reader = PdfReader(io.BytesIO(content))
    pages = [
        Page(page_number=i, text=(page.extract_text() or "").strip())
        for i, page in enumerate(reader.pages, start=1)
    ]
    title = reader.metadata.title if reader.metadata else None
    return ParsedDocument(mime_type=PDF_MIME, title=_clean_title(title), pages=pages)


def parse_docx(content: bytes) -> ParsedDocument:
    """Extract paragraph text from a DOCX file with python-docx.

    Args:
        content: Raw DOCX bytes.

    Returns:
        ParsedDocument with the DOCX mime type, title from the document's core
        properties (None if empty), and a single Page 1 holding all paragraphs
        joined by newlines.
    """
    doc = Document(io.BytesIO(content))
    text = "\n".join(p.text for p in doc.paragraphs)
    return ParsedDocument(
        mime_type=DOCX_MIME,
        title=_clean_title(doc.core_properties.title),
        pages=[Page(page_number=1, text=text.strip())],
    )


def parse_html(content: bytes) -> ParsedDocument:
    """Extract visible text from an HTML document with BeautifulSoup.

    Args:
        content: Raw HTML bytes.

    Returns:
        ParsedDocument with mime_type "text/html", title from <title> (None if
        missing), and a single Page 1 with the visible text. <script>, <style> and
        other non-visible content are removed.
    """
    soup = BeautifulSoup(content, "html.parser")
    title = _clean_title(soup.title.get_text()) if soup.title else None
    for tag in soup(_NON_VISIBLE_TAGS):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    text = "\n".join(line for line in lines if line)
    return ParsedDocument(mime_type=HTML_MIME, title=title, pages=[Page(1, text)])


def parse_text(content: bytes) -> ParsedDocument:
    """Decode a plain text or Markdown file.

    Args:
        content: Raw file bytes; decoded as UTF-8 (a leading BOM is stripped).

    Returns:
        ParsedDocument with mime_type "text/plain", title None, and a single Page 1
        with the decoded text. parse_document sets mime_type to "text/markdown" and
        the title to the first "# " heading for .md files.
    """
    text = content.decode("utf-8-sig")
    return ParsedDocument(mime_type=TEXT_MIME, title=None, pages=[Page(1, text.strip())])


def _clean_title(title: str | None) -> str | None:
    """Strip whitespace; empty titles become None."""
    if title is None:
        return None
    return title.strip() or None


_PARSERS: dict[str, Callable[[bytes], ParsedDocument]] = {
    PDF_MIME: parse_pdf,
    DOCX_MIME: parse_docx,
    HTML_MIME: parse_html,
    MARKDOWN_MIME: parse_text,
    TEXT_MIME: parse_text,
}
