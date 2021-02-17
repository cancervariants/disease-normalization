"""Test the therapy querying method."""
from disease.query import QueryHandler, InvalidParameterException
import pytest


@pytest.fixture(scope='module')
def query_handler():
    """Build query handler test fixture."""
    class QueryGetter:

        def __init__(self):
            self.query_handler = QueryHandler()

        def normalize(self, query_str, keyed=False, incl='', excl=''):
            resp = self.query_handler.search_sources(query_str=query_str,
                                                     keyed=keyed,
                                                     incl=incl, excl=excl)
            return resp

    return QueryGetter()


def test_query(query_handler):
    """Test that query returns properly-structured response."""
    resp = query_handler.normalize('Neuroblastoma', keyed=False)
    assert resp['query'] == 'Neuroblastoma'
    matches = resp['source_matches']
    assert isinstance(matches, list)
    assert len(matches) == 1
    ncit = list(filter(lambda m: m['source'] == 'NCIt',
                       matches))[0]
    assert len(ncit['records']) == 1
    ncit_record = ncit['records'][0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_keyed(query_handler):
    """Test that query structures matches as dict when requested."""
    resp = query_handler.normalize('Neuroblastoma', keyed=True)
    matches = resp['source_matches']
    assert isinstance(matches, dict)
    ncit = matches['NCIt']
    ncit_record = ncit['records'][0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_specify_query_handlers(query_handler):
    """Test inclusion and exclusion of sources in query."""
    # test full inclusion
    sources = 'ncit,mondo'
    resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                   incl=sources, excl='')
    matches = resp['source_matches']
    assert len(matches) == 2
    assert 'NCIt' in matches
    assert 'Mondo' in matches

    # test full exclusion
    resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                   excl=sources)
    matches = resp['source_matches']
    assert len(matches) == 0

    # test case insensitive
    resp = query_handler.normalize('Neuroblastoma', keyed=True, excl='NCIt')
    matches = resp['source_matches']
    assert 'NCIt' not in matches
    resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                   incl='nCiT')
    matches = resp['source_matches']
    assert 'NCIt' in matches

    # test error on invalid source names
    with pytest.raises(InvalidParameterException):
        resp = query_handler.normalize('Neuroblastoma', keyed=True, incl='nct')

    # test error for supplying both incl and excl args
    with pytest.raises(InvalidParameterException):
        resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                       incl='mondo', excl='ncit')
