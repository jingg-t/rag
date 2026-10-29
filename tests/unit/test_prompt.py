import pytest

# TODO: implement tests and remove the skip marker
pytestmark = pytest.mark.skip(reason="not implemented")


def test_format_citation_includes_source_and_page() -> None: ...


def test_build_messages_puts_context_before_question() -> None: ...


def test_extract_citations_maps_labels_to_chunks() -> None: ...


def test_extract_citations_ignores_unknown_labels() -> None: ...
