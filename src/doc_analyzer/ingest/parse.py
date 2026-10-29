"""Document bytes → text. Pure functions, no Spark imports."""

from __future__ import annotations

from dataclasses import dataclass, field


class ParseError(Exception):
    """Raised when a document cannot be parsed; recorded as parse_status='error' in silver."""


@dataclass(frozen=True)
class Page:
    """Text of one page. Formats without real pages (DOCX, HTML, TXT, MD) produce a single page 1."""

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
        # TODO: implement
        raise NotImplementedError


def compute_doc_id(content: bytes) -> str:
    """Content-addressed document id, so the same file uploaded twice gets the same id.

    Args:
        content: Raw file bytes.

    Returns:
        Lowercase sha256 hex digest of the bytes (64 characters).
    """
    # TODO: implement
    raise NotImplementedError


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
    # TODO: implement
    raise NotImplementedError


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
    # TODO: implement
    raise NotImplementedError


def parse_pdf(content: bytes) -> ParsedDocument:
    """Extract text per page from a PDF with pypdf.

    Args:
        content: Raw PDF bytes.

    Returns:
        ParsedDocument with mime_type "application/pdf", title from the PDF metadata
        (None if missing), and one Page per PDF page, numbered from 1. Pages with no
        extractable text are kept with empty text so page numbers stay correct.
    """
    # TODO: implement
    raise NotImplementedError


def parse_docx(content: bytes) -> ParsedDocument:
    """Extract paragraph text from a DOCX file with python-docx.

    Args:
        content: Raw DOCX bytes.

    Returns:
        ParsedDocument with the DOCX mime type, title from the document's core
        properties (None if empty), and a single Page 1 holding all paragraphs
        joined by newlines.
    """
    # TODO: implement
    raise NotImplementedError


def parse_html(content: bytes) -> ParsedDocument:
    """Extract visible text from an HTML document with BeautifulSoup.

    Args:
        content: Raw HTML bytes.

    Returns:
        ParsedDocument with mime_type "text/html", title from <title> (None if
        missing), and a single Page 1 with the visible text. <script>, <style> and
        other non-visible content are removed.
    """
    # TODO: implement
    raise NotImplementedError


def parse_text(content: bytes) -> ParsedDocument:
    """Decode a plain text or Markdown file.

    Args:
        content: Raw file bytes; decoded as UTF-8 (a leading BOM is stripped).

    Returns:
        ParsedDocument with mime_type "text/plain", title None, and a single Page 1
        with the decoded text. parse_document sets mime_type to "text/markdown" and
        the title to the first "# " heading for .md files.
    """
    # TODO: implement
    raise NotImplementedError
