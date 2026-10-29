import pytest

# TODO: implement tests using the spark fixture and remove the skip marker
pytestmark = [pytest.mark.integration, pytest.mark.skip(reason="not implemented")]


def test_pipeline_is_idempotent_on_rerun() -> None: ...


def test_reuploaded_file_does_not_duplicate_rows() -> None: ...


def test_parse_failure_is_recorded_not_raised() -> None: ...


def test_deleted_source_file_removes_silver_and_gold_rows() -> None: ...
