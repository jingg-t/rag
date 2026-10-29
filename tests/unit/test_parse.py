import pytest

# TODO: implement tests (with sample PDF/DOCX/HTML fixtures) and remove the skip marker
pytestmark = pytest.mark.skip(reason="not implemented")


def test_compute_doc_id_is_stable_for_same_bytes() -> None: ...


def test_detect_mime_type_for_each_supported_extension() -> None: ...


def test_parse_pdf_keeps_page_numbers() -> None: ...


def test_parse_docx_extracts_text() -> None: ...


def test_parse_html_drops_scripts_and_styles() -> None: ...


def test_parse_document_raises_parse_error_on_corrupt_file() -> None: ...
