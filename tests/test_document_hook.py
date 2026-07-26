import pytest

from atrium_paradata import ParadataLogger
from document_hook import write_document_record


@pytest.fixture
def mock_logger():
    """Provides a normalized ParadataLogger for testing."""
    # Provide a dummy config to satisfy the required positional argument
    dummy_config = {}
    logger = ParadataLogger(program="alto-postprocess", config=dummy_config)
    logger.run_id = "260725-101112"

    # Mock the get_license_block method in case it relies on a fully initialized config
    logger.get_license_block = lambda: {"effective_license": "CC BY-NC-SA 4.0"}
    return logger


def test_blocks_passed_through_untouched(mock_logger):
    """Contract Rule 2 & 6: Own block only, everything else (and newer blocks) pass through."""
    baseline = {"entities": [{"surface": "Praha", "type_onto": "GPE"}], "future_spec_block": {"metadata": "preserved"}}

    result = write_document_record(baseline, None, None, mock_logger)

    assert "entities" in result
    assert result["entities"] == [{"surface": "Praha", "type_onto": "GPE"}]
    assert "future_spec_block" in result
    assert result["future_spec_block"] == {"metadata": "preserved"}


def test_no_baseline_creates_standalone(mock_logger):
    """Contract Rule 3: No baseline -> own part only (standalone-safe)."""
    result = write_document_record(None, None, None, mock_logger)

    assert "pages" in result
    assert "lines" in result
    assert "content" in result
    assert result["assembled"]["source_run_ids"]["pages"] == mock_logger.run_id


def test_provenance_and_license_stamped(mock_logger):
    """Contract Rule 4 & 5: Run ID and effective License are stamped."""
    result = write_document_record({}, None, None, mock_logger)

    assert result["provenance"]["paradata_ref"] == f"paradata/{mock_logger.run_id}_pipeline-run.json"
    assert "license_detail" in result["provenance"]
    assert result["assembled"]["source_run_ids"]["content"] == mock_logger.run_id
