"""Test OMIM source."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler


@pytest.fixture(scope='module')
def omim():
    """Build OMIM ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='ncit')
            return response['source_matches']['NCIt']
    return QueryGetter()


@pytest.fixture(scope='module')
def mafd2():
    """Build MAFD2 test fixture."""
    return {
        "concept_id": "omim:309200",
        "label": "MAJOR AFFECTIVE DISORDER 2",
        "aliases": [
            "MAFD2",
            "MANIC-DEPRESSIVE ILLNESS",
            "MDI",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "MDX",
            "BIPOLAR AFFECTIVE DISORDER",
            "BPAD"
        ]
    }


@pytest.fixture(scope='module')
def acute_ll():
    """Build ALL fixture."""
    return {
        "concept_id": "omim:613065",
        "label": "LEUKEMIA, ACUTE LYMPHOBLASTIC",
        "aliases": [
            "ALL",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO, 1",
            "ALL1",
            "LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1",
            "LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, T-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
            "LEUKEMIA, ACUTE LYMPHOBLASTIC, B-HYPERDIPLOID, SUSCEPTIBILITY TO"
        ]
    }


@pytest.fixture(scope='module')
def lall():
    """Build LALL fixture."""
    return {
        "concept_id": "omim:247640",
        "label": "LYMPHOBLASTIC LEUKEMIA, ACUTE, WITH LYMPHOMATOUS FEATURES",
        "aliases": [
            "LALL",
            "LYMPHOMATOUS ALL"
        ]
    }


def test_concept_id_match(omim, mafd2, acute_ll, lall, provide_comparator):
    """Test concept ID search resolution."""
    compare_records = provide_comparator()
    response = omim.search('omim:309200')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, mafd2)

    compare_records = provide_comparator()
    response = omim.search('omim:613065')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    compare_records = provide_comparator()
    response = omim.search('omim:247640')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, lall)


def test_label_match(omim, mafd2, acute_ll, lall, provide_comparator):
    """Test label search resolution."""
    pass
