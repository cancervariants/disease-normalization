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


@pytest.fixture(scope='module')
def neuroblastoma():
    """Build neuroblastoma test fixture."""
    return {
        "label_and_type": "ncit:c3270##identity",
        "concept_id": "ncit:C3270",
        "label": "Neuroblastoma",
        "aliases": [
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (NBL)",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma, NOS",
            "neuroblastoma"
        ],
        "other_identifiers": [],
        "xrefs": ["umls:C0027819"],
        "src_name": "NCIt"
    }


def test_query(query_handler):
    """Test that query returns properly-structured response."""
    resp = query_handler.normalize('Neuroblastoma', keyed=False)
    assert resp['query'] == 'Neuroblastoma'
    matches = resp['source_matches']
    assert isinstance(matches, list)
    assert len(matches) == 1
    wikidata = list(filter(lambda m: m['source'] == 'NCIt',
                           matches))[0]
    assert len(wikidata['records']) == 1
    wikidata_record = wikidata['records'][0]
    assert wikidata_record.label == 'Neuroblastoma'


def test_query_keyed(query_handler):
    """Test that query structures matches as dict when requested."""
    resp = query_handler.normalize('Neuroblastoma', keyed=True)
    matches = resp['source_matches']
    assert isinstance(matches, dict)
    chemidplus = matches['NCIt']
    chemidplus_record = chemidplus['records'][0]
    assert chemidplus_record.label == 'Neuroblastoma'


def test_query_specify_query_handlers(query_handler):
    """Test inclusion and exclusion of sources in query."""
    # test full inclusion
    sources = 'ncit'
    resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                   incl=sources, excl='')
    matches = resp['source_matches']
    assert len(matches) == 1
    assert 'NCIt' in matches

    # test full exclusion
    resp = query_handler.normalize('Neuroblastoma', keyed=True,
                                   excl='ncit')
    matches = resp['source_matches']
    assert len(matches) == 0
    assert 'NCIt' not in matches

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
                                       incl='ncit', excl='ncit')
