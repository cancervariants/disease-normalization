"""This module contains data models for representing VICC normalized
disease records.
"""
from enum import Enum, IntEnum


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    NAME = 80
    ALIAS = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(Enum):
    """Define string constraints to ensure consistent capitalization."""

    NCIT = "NCIt"


class SourceIDAfterNamespace(Enum):
    """Define string constraints after namespace."""

    NCIT = "C"  # TODO double check that this is accurate


class NamespacePrefix(Enum):
    """Define string constraints for namespace prefixes on concept IDs."""

    NCIT = "ncit"
