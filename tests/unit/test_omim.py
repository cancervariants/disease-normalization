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
                                                         incl='omim')
            return response['source_matches']['OMIM']
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
        ],
        "other_identifiers": [],
        "xrefs": [],
        "pediatric_disease": None,
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
        ],
        "other_identifiers": [],
        "xrefs": [],
        "pediatric_disease": None,
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
        ],
        "other_identifiers": [],
        "xrefs": [],
        "pediatric_disease": None,
    }


def test_concept_id_match(omim, mafd2, acute_ll, lall, compare_records):
    """Test concept ID search resolution."""
    response = omim.search('omim:309200')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, mafd2)

    response = omim.search('omim:613065')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    response = omim.search('omim:247640')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, lall)


def test_label_match(omim, mafd2, acute_ll, lall, compare_records):
    """Test label search resolution."""
    response = omim.search('MAJOR AFFECTIVE DISORDER 2')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, mafd2)

    response = omim.search('LEUKEMIA, ACUTE LYMPHOBLASTIC')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    response = omim.search('lymphoblastic leukemia, acute, with lymphomatous features')  # noqa: E501
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, lall)


def test_alias_match(omim, mafd2, acute_ll, lall, compare_records):
    """Test alias search resolution."""
    response = omim.search('bipolar affective disorder')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) >= 1
    actual_disease = None
    for record in response['records']:
        if record.label == 'MAJOR AFFECTIVE DISORDER 2':
            actual_disease = record.dict()
    compare_records(actual_disease, mafd2)

    response = omim.search('bpad')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) >= 1
    actual_disease = None
    for record in response['records']:
        if record.label == 'MAJOR AFFECTIVE DISORDER 2':
            actual_disease = record.dict()
    compare_records(actual_disease, mafd2)

    response = omim.search('mafd2')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, mafd2)

    response = omim.search('all')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    response = omim.search('LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    response = omim.search('LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO')  # noqa: E501
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, acute_ll)

    response = omim.search('lymphomatous all')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, lall)

    response = omim.search('lall')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, lall)


def test_meta(omim):
    """Test that meta field is correct."""
    response = omim.search('irrelevant-search-string')
    assert response['source_meta_'].data_license == 'custom'
    assert response['source_meta_'].data_license_url == \
        'https://omim.org/help/agreement'
    assert response['source_meta_'].version == '20210304'
    assert response['source_meta_'].data_url == 'https://www.omim.org/downloads'  # noqa: E501
    assert response['source_meta_'].rdp_url == 'http://reusabledata.org/omim.html'  # noqa: E501
    assert response['source_meta_'].data_license_attributes == {
        "non_commercial": False,
        "share_alike": True,
        "attribution": True
    }
