"""Test the therapy querying method."""
from disease.query import QueryHandler, InvalidParameterException
from disease.schemas import MatchType
import pytest


@pytest.fixture(scope='module')
def query_handler():
    """Build query handler test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def search(self, query_str, keyed=False, incl='', excl=''):
            resp = self.query_handler.search_sources(query_str=query_str,
                                                     keyed=keyed,
                                                     incl=incl, excl=excl)
            return resp

        def normalize(self, query_str):
            return self.query_handler.search_groups(query_str)
            # response = self.query_handler.search_groups(query_str)
            # print(response)
            # return response

    return QueryGetter()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return {
        "concept_ids": [
            "ncit:C3270",
            "mondo:0005072",
            "oncotree:NBL",
            "DOID:769"
        ],
        "label": "Neuroblastoma",
        "aliases": [
            "neuroblastoma",
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "Neuroblastoma, NOS",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma (NBL)",
            "neural Crest tumor, malignant",
            "neuroblastoma, malignant"
        ],
        "xrefs": [
            "umls:C0027819",
            "icd.o:9500/3",
            "efo:0000621",
            "gard:7185",
            "gard:0007185",
            "icd:C74.9",
            "icd.o:9500/3",
            "icd.o:M9500/3",
            "mesh:D009447",
            "meddra:10029260",
            "nifstd:birnlex_12631",
            "orphanet:635",
            "umls:CN205405"
        ],
        "pediatric": None
    }


@pytest.fixture(scope='module')
def skin_myo():
    """Create a test fixture for skin myopithelioma"""
    return {
        "concept_ids": ["ncit:C167370"],
        "label": "Skin Myoepithelioma",
        "aliases": ["Cutaneous Myoepithelioma"],
        "other_identifiers": [],
        "xrefs": [],
    }


def test_query(query_handler):
    """Test that query returns properly-structured response."""
    resp = query_handler.search('Neuroblastoma', keyed=False)
    assert resp['query'] == 'Neuroblastoma'
    matches = resp['source_matches']
    assert isinstance(matches, list)
    assert len(matches) == 4
    ncit = list(filter(lambda m: m['source'] == 'NCIt',
                       matches))[0]
    assert len(ncit['records']) == 1
    ncit_record = ncit['records'][0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_keyed(query_handler):
    """Test that query structures matches as dict when requested."""
    resp = query_handler.search('Neuroblastoma', keyed=True)
    matches = resp['source_matches']
    assert isinstance(matches, dict)
    ncit = matches['NCIt']
    ncit_record = ncit['records'][0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_specify_query_handlers(query_handler):
    """Test inclusion and exclusion of sources in query."""
    # test full inclusion
    sources = 'ncit,mondo,do,oncotree'
    resp = query_handler.search('Neuroblastoma', keyed=True,
                                incl=sources, excl='')
    matches = resp['source_matches']
    assert len(matches) == 4
    assert 'NCIt' in matches
    assert 'Mondo' in matches
    assert 'DO' in matches
    assert 'OncoTree' in matches

    # test full exclusion
    resp = query_handler.search('Neuroblastoma', keyed=True,
                                excl=sources)
    matches = resp['source_matches']
    assert len(matches) == 0

    # test case insensitive
    resp = query_handler.search('Neuroblastoma', keyed=True, excl='NCIt')
    matches = resp['source_matches']
    assert 'NCIt' not in matches
    resp = query_handler.search('Neuroblastoma', keyed=True,
                                incl='nCiT')
    matches = resp['source_matches']
    assert 'NCIt' in matches

    # test error on invalid source names
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search('Neuroblastoma', keyed=True, incl='nct')

    # test error for supplying both incl and excl args
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search('Neuroblastoma', keyed=True,
                                    incl='mondo', excl='ncit')


def test_normalize_query(query_handler, neuroblastoma, compare_merged_records):
    """Test that normalized endpoint correctly resolves queries."""
    response = query_handler.normalize('Neuroblastoma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['meta_']) == 4
    compare_merged_records(response['record'], neuroblastoma)
    assert 'NCIt' in response['meta_']
    assert 'DO' in response['meta_']
    assert 'Mondo' in response['meta_']
    assert 'Oncotree' in response['meta_']


def test_normalize_non_mondo(query_handler, skin_myo, compare_merged_records):
    """Test that normalize endpoint returns records not in Mondo groups."""
    response = query_handler.normalize('Skin Myoepithelioma')
    assert response['match_type'] == MatchType.LABEL
    assert len(response['meta_']) == 1
    compare_merged_records(response['record'], skin_myo)
    assert 'NCIt' in response['meta_']

    response = query_handler.normalize('Cutaneous Myoepithelioma')
    assert response['match_type'] == MatchType.ALIAS
    assert len(response['meta_']) == 1
    compare_merged_records(response['record'], skin_myo)
    assert 'NCIt' in response['meta_']
