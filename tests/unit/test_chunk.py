import pytest

# TODO: implement tests and remove the skip marker
pytestmark = pytest.mark.skip(reason="not implemented")


def test_empty_text_yields_no_chunks() -> None: ...


def test_short_text_yields_single_chunk() -> None: ...


def test_chunks_respect_token_limit() -> None: ...


def test_consecutive_chunks_overlap() -> None: ...


def test_chunks_keep_page_metadata() -> None: ...


def test_make_chunk_id_format() -> None: ...
