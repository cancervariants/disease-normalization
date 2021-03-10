"""Test MONDO ETL methods."""
import pytest
from disease.schemas import MatchType
from disease.query import QueryHandler


@pytest.fixture(scope='module')
def mondo():
    """Build Mondo ETL test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str):
            response = self.query_handler.search_sources(query_str, keyed=True,
                                                         incl='mondo')
            return response['source_matches']['Mondo']
    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Construct a test fixture for neuroblastoma"""
    return {
        "concept_id": "mondo:0005072",
        "label": "neuroblastoma",
        "aliases": [
            "neural Crest tumor, malignant",
            "neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma, malignant"
        ],
        "other_identifiers": [
            "ncit:C3270",
            "DOID:769",
            "oncotree:NBL",
        ],
        "xrefs": [
            "orphanet:635",
            "nifstd:birnlex_12631",
            "umls:C0027819",
            "gard:0007185",
            "meddra:10029260",
            "icd.o:9500/3",
            "umls:CN205405",
            "efo:0000621",
            "icd:C74.9",
            "mesh:D009447"
        ],
        "pediatric_disease": None,
    }


@pytest.fixture(scope='module')
def richter_syndrome():
    """Construct a test fixture for Richter Syndrome"""
    return {
        "concept_id": "mondo:0002083",
        "label": "Richter syndrome",
        "aliases": [
            "Richter's syndrome",
            "Richter transformation",
            "Richter's transformation"
        ],
        "other_identifiers": ["ncit:C35424", "DOID:1703"],
        "xrefs": [
            "icd:C91.1",
            "umls:C0349631",
            "gard:0007578",
        ],
        "pediatric_disease": None,
    }


@pytest.fixture(scope='module')
def pediatric_liposarcoma():
    """Construct a test fixture for pediatric liposarcoma. Tests the
    pediatric flag.
    """
    return {
        "concept_id": "mondo:0003587",
        "label": "pediatric liposarcoma",
        "aliases": [
            "childhood liposarcoma",
            "liposarcoma"
        ],
        "other_identifiers": ["DOID:5695", "ncit:C8091"],
        "xrefs": [
            "umls:C0279984"
        ],
        "pediatric_disease": True,
    }


@pytest.fixture(scope="module")
def cystic_teratoma_adult():
    """Construct a test fixture for adult cystic teratoma. Tests the
    pediatric flag.
    """
    return {
        "concept_id": "mondo:0004099",
        "label": "adult cystic teratoma",
        "aliases": ["cystic teratoma of adults"],
        "pediatric_disease": None,
        "other_identifiers": ["ncit:C9012", "DOID:7079"],
        "xrefs": ["umls:C1368888"],
    }


def test_concept_id_match(mondo, neuroblastoma, richter_syndrome,
                          pediatric_liposarcoma, compare_records):
    """Test that concept ID search resolves to correct record"""
    response = mondo.search('mondo:0005072')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('mondo:0002083')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search('MONDO:0005072')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('mondo:0003587')
    assert response['match_type'] == MatchType.CONCEPT_ID
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = mondo.search('0002083')
    assert response['match_type'] == MatchType.NO_MATCH


def test_label_match(mondo, neuroblastoma, richter_syndrome,
                     pediatric_liposarcoma, cystic_teratoma_adult,
                     compare_records):
    """Test that label search resolves to correct record."""
    response = mondo.search('Neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('NEUROBLASTOMA')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('richter syndrome')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search('pediatric liposarcoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, pediatric_liposarcoma)

    response = mondo.search('Adult Cystic Teratoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, cystic_teratoma_adult)


def test_alias_match(mondo, neuroblastoma, richter_syndrome, compare_records):
    """Test that alias search resolves to correct record."""
    response = mondo.search('neuroblastoma, malignant')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('RICHTER TRANSFORMATION')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search('Neuroblastoma, Malignant')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search('neuroblastoma (Schwannian Stroma-poor)')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, neuroblastoma)

    response = mondo.search("Richter's transformation")
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("Richter's syndrome")
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['records']) == 1
    actual_disease = response['records'][0].dict()
    compare_records(actual_disease, richter_syndrome)

    response = mondo.search("neuroblastoma Schwannian Stroma-poor")
    assert response['match_type'] == MatchType.NO_MATCH


def test_meta(mondo):
    """Test that meta field is correct."""
    response = mondo.search('neuroblastoma')
    assert response['meta_'].data_license == 'CC BY 4.0'
    assert response['meta_'].data_license_url == \
        'https://creativecommons.org/licenses/by/4.0/legalcode'
    assert response['meta_'].version == '20210129'
    assert response['meta_'].data_url == \
        'https://mondo.monarchinitiative.org/pages/download/'
    assert response['meta_'].rdp_url == 'http://reusabledata.org/monarch.html'
    assert response['meta_'].data_license_attributes == {
        "non_commercial": False,
        "share_alike": False,
        "attribution": True
    }
