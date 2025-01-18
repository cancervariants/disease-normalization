"""Module to test the schemas module."""

from disease.schemas import NAMESPACE_TO_SYSTEM_URI, NamespacePrefix


def test_namespace_to_system_uri():
    """Ensure that each NamespacePrefix is included in NAMESPACE_TO_SYSTEM_URI"""
    for v in NamespacePrefix.__members__.values():
        assert v in NAMESPACE_TO_SYSTEM_URI, v
        assert NAMESPACE_TO_SYSTEM_URI[v].startswith("http"), v
