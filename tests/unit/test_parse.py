import hashlib
import io
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfReader

from doc_analyzer.ingest.parse import (
    Page,
    ParsedDocument,
    ParseError,
    compute_doc_id,
    detect_mime_type,
    parse_document,
    parse_docx,
    parse_html,
    parse_pdf,
    parse_text,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx_bytes(paragraphs: list[str], title: str = "") -> bytes:
    doc = Document()
    doc.core_properties.title = title
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --- ParsedDocument ---------------------------------------------------------------------------


def test_parsed_document_text_joins_pages_with_blank_line() -> None:
    doc = ParsedDocument("text/plain", None, [Page(1, "one"), Page(2, "two")])
    assert doc.text == "one\n\ntwo"


def test_parsed_document_text_is_empty_without_pages() -> None:
    assert ParsedDocument("text/plain", None).text == ""


# --- compute_doc_id ---------------------------------------------------------------------------


def test_compute_doc_id_is_stable_for_same_bytes() -> None:
    content = b"same file uploaded twice"
    assert compute_doc_id(content) == compute_doc_id(content)
    assert compute_doc_id(content) == hashlib.sha256(content).hexdigest()


def test_compute_doc_id_is_lowercase_hex_sha256() -> None:
    doc_id = compute_doc_id(b"abc")
    assert len(doc_id) == 64
    assert doc_id == doc_id.lower()
    int(doc_id, 16)  # valid hex


def test_compute_doc_id_differs_for_different_bytes() -> None:
    assert compute_doc_id(b"a") != compute_doc_id(b"b")


# --- detect_mime_type -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "content", "expected"),
    [
        ("docs/report.pdf", b"%PDF-1.7\n...", "application/pdf"),
        ("docs/policy.docx", b"PK\x03\x04...", DOCX_MIME),
        ("docs/page.html", b"<html><body>hi</body></html>", "text/html"),
        ("docs/readme.md", b"# Title\n", "text/markdown"),
        ("docs/notes.txt", b"plain text", "text/plain"),
        ("docs/REPORT.PDF", b"%PDF-1.7\n...", "application/pdf"),
    ],
)
def test_detect_mime_type_for_each_supported_extension(
    path: str, content: bytes, expected: str
) -> None:
    assert detect_mime_type(path, content) == expected


def test_detect_mime_type_unknown_extension() -> None:
    assert detect_mime_type("tool.exe", b"MZ...") == "application/octet-stream"


@pytest.mark.parametrize(
    ("path", "content"),
    [("fake.pdf", b"not a pdf"), ("fake.docx", b"not a zip")],
)
def test_detect_mime_type_rejects_wrong_magic_bytes(path: str, content: bytes) -> None:
    assert detect_mime_type(path, content) == "application/octet-stream"


# --- parse_pdf --------------------------------------------------------------------------------


def test_parse_pdf_keeps_page_numbers() -> None:
    content = (FIXTURES / "pdf-sample_0.pdf").read_bytes()
    expected_pages = len(PdfReader(io.BytesIO(content)).pages)

    doc = parse_pdf(content)

    assert doc.mime_type == "application/pdf"
    assert [p.page_number for p in doc.pages] == list(range(1, expected_pages + 1))
    assert any(p.text.strip() for p in doc.pages)


# --- parse_docx -------------------------------------------------------------------------------


def test_parse_docx_extracts_text() -> None:
    content = _docx_bytes(["First paragraph.", "Second paragraph."], title="Policy")

    doc = parse_docx(content)

    assert doc.mime_type == DOCX_MIME
    assert doc.title == "Policy"
    assert doc.pages == [Page(1, "First paragraph.\nSecond paragraph.")]


def test_parse_docx_without_title_gives_none() -> None:
    assert parse_docx(_docx_bytes(["text"])).title is None


# --- parse_html -------------------------------------------------------------------------------


def test_parse_html_drops_scripts_and_styles() -> None:
    content = b"""<html><head><title>FAQ</title>
        <style>.hidden { color: red; }</style>
        <script>alert("tracking")</script>
        </head><body><h1>Refunds</h1><p>Refunds take 30 days.</p></body></html>"""

    doc = parse_html(content)

    assert doc.mime_type == "text/html"
    assert doc.title == "FAQ"
    assert len(doc.pages) == 1
    assert doc.pages[0].page_number == 1
    text = doc.pages[0].text
    assert "Refunds take 30 days." in text
    assert "alert" not in text
    assert "color: red" not in text


def test_parse_html_without_title_gives_none() -> None:
    assert parse_html(b"<html><body><p>hi</p></body></html>").title is None


# --- parse_text -------------------------------------------------------------------------------


def test_parse_text_decodes_utf8_and_strips_bom() -> None:
    doc = parse_text("﻿café notes".encode())

    assert doc.mime_type == "text/plain"
    assert doc.title is None
    assert doc.pages == [Page(1, "café notes")]


# --- parse_document ---------------------------------------------------------------------------


def test_parse_document_dispatches_pdf() -> None:
    content = (FIXTURES / "pdf-sample_0.pdf").read_bytes()
    assert parse_document("uploads/pdf-sample_0.pdf", content).mime_type == "application/pdf"


def test_parse_document_markdown_uses_first_heading_as_title() -> None:
    doc = parse_document("readme.md", b"intro\n# Getting Started\nbody\n## Next\n")

    assert doc.mime_type == "text/markdown"
    assert doc.title == "Getting Started"


def test_parse_document_raises_parse_error_on_corrupt_file() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_document("broken.pdf", b"%PDF-1.7 truncated garbage")
    assert exc_info.value.__cause__ is not None


def test_parse_document_raises_parse_error_on_unsupported_type() -> None:
    with pytest.raises(ParseError):
        parse_document("tool.exe", b"MZ...")


def test_parse_document_raises_parse_error_when_no_text() -> None:
    with pytest.raises(ParseError):
        parse_document("empty.txt", b"   \n\n ")
