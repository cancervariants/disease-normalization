"""Test MONDO ETL methods."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler
from typing import Dict


@pytest.fixture(scope='module')
def mondo():
    """Build MONDO ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='mondo')
            return response['source_matches']['MONDO']
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Construct a test fixture for neuroblastoma"""
    return {
        "concept_id": "mondo:0005072",
        "label": "neuroblastoma",
        "aliases": [
            "neuroblastoma",
            "neural Crest tumor, malignant",
            "neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma, malignant"
        ],
        "other_identifiers": ["ncit:C3270"],
        "xrefs": [
            "orphanet:635",
            "nifstd:birnlex_12631",
            "umls:C0027819",
            "doid:769",
            "gard:0007185",
            "meddra:10029260",
            "icdo:9500/3",
            "sctid:432328008",
            "umls:CN205405",
            "efo:0000621",
            "icd10:C74.9",
            "oncotree:NBL",
            "mesh:D009447"]
    }


def compare_records(actual_record: Dict, fixture_record: Dict):
    """Check that identity records are identical."""
    assert actual_record['concept_id'] == fixture_record['concept_id']
    assert ('label' in actual_record) == ('label' in fixture_record)
    if 'label' in actual_record or 'label' in fixture_record:
        assert actual_record['label'] == fixture_record['label']
    assert ('aliases' in actual_record) == ('aliases' in fixture_record)
    if 'aliases' in actual_record or 'aliases' in fixture_record:
        assert set(actual_record['aliases']) == set(fixture_record['aliases'])
    assert ('other_identifiers' in actual_record) == ('other_identifiers' in fixture_record)  # noqa: E501
    if 'other_identifiers' in actual_record or 'other_identifiers' in fixture_record:  # noqa: E501
        assert set(actual_record['other_identifiers']) == set(fixture_record['other_identifiers'])  # noqa: E501
    assert ('xrefs' in actual_record) == ('xrefs' in fixture_record)
    if 'xrefs' in actual_record or 'xrefs' in fixture_record:
        assert set(actual_record['xrefs']) == set(fixture_record['xrefs'])



