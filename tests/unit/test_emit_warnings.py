"""Test the emit_warnings function."""

from disease.query import QueryHandler


def test_emit_warnings(database):
    """Test that emit_warnings works correctly."""
    expected_warnings = {"nbsp": "Query contains non breaking space characters."}
    query_handler = QueryHandler(database)

    # Test emit no warnings
    actual_warnings = query_handler._emit_warnings("CISPLATIN")
    assert actual_warnings is None

    # Test emit warnings
    actual_warnings = query_handler._emit_warnings("CIS PLATIN")
    assert actual_warnings == actual_warnings

    actual_warnings = query_handler._emit_warnings("CIS\u00a0platin")
    assert expected_warnings == actual_warnings

    actual_warnings = query_handler._emit_warnings("CIS&nbsp;platin")
    assert expected_warnings == actual_warnings

    actual_warnings = query_handler._emit_warnings("CIS\xa0platin")
    assert expected_warnings == actual_warnings
