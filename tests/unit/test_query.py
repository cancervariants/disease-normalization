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

    return QueryGetter()


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


def compare_merged_records(actual_record, fixture_record):
    """Check that records are identical."""
    assert set(actual_record['concept_ids']) == \
        set(fixture_record['concept_ids'])
    assert ('label' in actual_record) == ('label' in fixture_record)
    if 'label' in actual_record or 'label' in fixture_record:
        assert actual_record['label'] == fixture_record['label']
    assert ('aliases' in actual_record) == ('aliases' in fixture_record)
    if 'aliases' in actual_record or 'aliases' in fixture_record:
        assert set(actual_record['aliases']) == set(fixture_record['aliases'])
    assert ('xrefs' in actual_record) == ('xrefs' in fixture_record)
    if 'xrefs' in actual_record or 'xrefs' in fixture_record:
        assert set(actual_record['xrefs']) == set(fixture_record['xrefs'])
    assert ('pediatric_disease' in actual_record) == \
        ('pediatric_disease' in fixture_record)
    if 'pediatric_disease' in actual_record or \
            'pediatric_disease' in fixture_record:
        assert actual_record['pediatric_disease'] == \
            fixture_record['pediatric_disease']


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


def test_normalize_non_mondo(query_handler, skin_myo):
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
