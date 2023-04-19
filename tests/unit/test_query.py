"""Test the therapy querying method."""
from ga4gh.vrsatile.pydantic.vrsatile_models import ValueObjectDescriptor
from disease.query import QueryHandler, InvalidParameterException
from disease.schemas import MatchType, SourceName
import pytest
from datetime import datetime


@pytest.fixture(scope="module")
def query_handler():
    """Build query handler test fixture"""
    return QueryHandler()


@pytest.fixture(scope='module')
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return ValueObjectDescriptor(**{
        "id": "normalize.disease:Neuroblastoma",
        "type": "DiseaseDescriptor",
        "disease_id": "ncit:C3270",
        "label": "Neuroblastoma",
        "xrefs": [
            "mondo:0005072",
            "oncotree:NBL",
            "DOID:769"
        ],
        "alternate_labels": [
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
        "extensions": [
            {
                "type": "Extension",
                "name": "associated_with",
                "value": [
                    "umls:C0027819",
                    "icdo:9500/3",
                    "efo:0000621",
                    "gard:7185",
                    "gard:0007185",
                    "icdo:9500/3",
                    "mesh:D009447",
                    "orphanet:635",
                    "umls:CN205405",
                    "umls:C2751421"
                ]
            }
        ]
    })


@pytest.fixture(scope='module')
def skin_myo():
    """Create a test fixture for skin myopithelioma"""
    return ValueObjectDescriptor(**{
        "id": "normalize.disease:Skin Myoepithelioma",
        "type": "DiseaseDescriptor",
        "disease_id": "ncit:C167370",
        "label": "Skin Myoepithelioma",
        "alternate_labels": ["Cutaneous Myoepithelioma"],
    })


@pytest.fixture(scope='module')
def mafd2():
    """Create a test fixture for major affective disorder 2. Query should not
    include a "pediatric_disease" Extension object.
    """
    return ValueObjectDescriptor(**{
        "id": "normalize.disease:MAFD2",
        "type": "DiseaseDescriptor",
        "disease_id": "mondo:0010648",
        "label": "major affective disorder 2",
        "alternate_labels": [
            "MAFD2",
            "MDI",
            "MDX",
            "MANIC-DEPRESSIVE ILLNESS",
            "BPAD",
            "MAFD2",
            "BIPOLAR AFFECTIVE DISORDER",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "major affective disorder 2, X-linked dominant"
        ],
        "xrefs": [
            "omim:309200"
        ],
        "extensions": [
            {
                "type": "Extension",
                "name": "associated_with",
                "value": [
                    "mesh:C564108"
                ]
            }
        ]
    })


def compare_vod(actual, fixture):
    """Verify correctness of returned VOD object against test fixture."""
    actual = actual.disease_descriptor
    assert actual.id == fixture.id
    assert actual.type == fixture.type
    assert actual.disease_id == fixture.disease_id
    assert actual.label == fixture.label

    assert (actual.xrefs is not None) == (fixture.xrefs is not None)
    if actual.xrefs is not None and fixture.xrefs is not None:
        assert set(actual.xrefs) == set(fixture.xrefs)

    assert ((actual.alternate_labels is not None) ==
            (fixture.alternate_labels is not None))
    if (actual.alternate_labels is not None) and \
            (fixture.alternate_labels is not None):
        assert set(actual.alternate_labels) == set(fixture.alternate_labels)

    def get_extension(extensions, name):
        matches = [e for e in extensions if e.name == name]
        if len(matches) > 1:
            assert False
        elif len(matches) == 1:
            return matches[0]
        else:
            return None

    assert (actual.extensions is not None) == (fixture.extensions is not None)
    if actual.extensions is not None and fixture.extensions is not None:
        ext_actual = actual.extensions
        ext_fixture = fixture.extensions

        assoc_actual = get_extension(ext_actual, 'associated_with')
        assoc_fixture = get_extension(ext_fixture, 'associated_with')
        assert (assoc_actual is None) == (assoc_fixture is None)
        if assoc_actual and assoc_fixture:
            assert set(assoc_actual.value) == set(assoc_fixture.value)
            assert assoc_actual.value

        ped_actual = get_extension(ext_actual, 'pediatric_disease')
        ped_fixture = get_extension(ext_fixture, 'pediatric_disease')
        assert (ped_actual is None) == (ped_fixture is None)
        if ped_actual and ped_fixture:
            assert set(ped_actual.value) == set(ped_fixture.value)
            assert ped_actual.value


def test_query(query_handler):
    """Test that query returns properly-structured response."""
    resp = query_handler.search('Neuroblastoma', keyed=False)
    assert resp.query == 'Neuroblastoma'
    matches = resp.source_matches
    assert isinstance(matches, list)
    assert len(matches) == 5
    ncit = list(filter(lambda m: m.source == SourceName.NCIT, matches))[0]
    assert len(ncit.records) == 1
    ncit_record = ncit.records[0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_keyed(query_handler):
    """Test that query structures matches as dict when requested."""
    resp = query_handler.search('Neuroblastoma', keyed=True)
    matches = resp.source_matches
    assert isinstance(matches, dict)
    ncit = matches[SourceName.NCIT]
    ncit_record = ncit.records[0]
    assert ncit_record.label == 'Neuroblastoma'


def test_query_specify_query_handlers(query_handler):
    """Test inclusion and exclusion of sources in query."""
    # test full inclusion
    sources = 'ncit,mondo,do,oncotree,omim'
    resp = query_handler.search('Neuroblastoma', keyed=True, incl=sources, excl='')
    matches = resp.source_matches
    assert len(matches) == 5
    assert SourceName.NCIT in matches
    assert SourceName.MONDO in matches
    assert SourceName.DO in matches
    assert SourceName.ONCOTREE in matches
    assert SourceName.OMIM in matches

    # test full exclusion
    resp = query_handler.search('Neuroblastoma', keyed=True, excl=sources)
    matches = resp.source_matches
    assert len(matches) == 0

    # test case insensitive
    resp = query_handler.search('Neuroblastoma', keyed=True, excl='NCIt')
    matches = resp.source_matches
    assert SourceName.NCIT not in matches
    resp = query_handler.search('Neuroblastoma', keyed=True, incl='nCiT')
    matches = resp.source_matches
    assert SourceName.NCIT in matches

    # test error on invalid source names
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search('Neuroblastoma', keyed=True, incl='nct')

    # test error for supplying both incl and excl args
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search(
            'Neuroblastoma', keyed=True, incl='mondo', excl='ncit'
        )


def test_normalize_query(query_handler, neuroblastoma, mafd2):
    """Test that normalized endpoint correctly resolves queries, and utilizes
    the VOD schema.
    """
    response = query_handler.normalize('Neuroblastoma')
    assert response.match_type == MatchType.LABEL
    assert response.warnings is None
    compare_vod(response, neuroblastoma)
    assert len(response.source_meta_) == 4
    assert SourceName.NCIT in response.source_meta_
    assert SourceName.DO in response.source_meta_
    assert SourceName.MONDO in response.source_meta_
    assert SourceName.ONCOTREE in response.source_meta_

    response = query_handler.normalize('MAFD2')
    assert response.match_type == MatchType.ALIAS
    assert response.warnings is None
    compare_vod(response, mafd2)
    assert len(response.source_meta_) == 2
    assert SourceName.MONDO in response.source_meta_


def test_normalize_non_mondo(query_handler, skin_myo, neuroblastoma):
    """Test that normalize endpoint returns records not in Mondo groups."""
    response = query_handler.normalize('Skin Myoepithelioma')
    assert response.match_type == MatchType.LABEL
    assert len(response.source_meta_) == 1
    skin_myo_alias = skin_myo.copy()
    skin_myo_alias.id = 'normalize.disease:Skin%20Myoepithelioma'
    compare_vod(response, skin_myo_alias)
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize('Cutaneous Myoepithelioma')
    assert response.match_type == MatchType.ALIAS
    assert len(response.source_meta_) == 1
    skin_myo_alias = skin_myo.copy()
    skin_myo_alias.id = 'normalize.disease:Cutaneous%20Myoepithelioma'
    compare_vod(response, skin_myo_alias)
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize('orphanet:635')
    assert response.match_type == MatchType.XREF
    assert len(response.source_meta_) == 4
    neuroblastoma_alias = neuroblastoma.copy()
    neuroblastoma_alias.id = 'normalize.disease:orphanet%3A635'
    compare_vod(response, neuroblastoma_alias)
    assert SourceName.NCIT in response.source_meta_
    assert SourceName.DO in response.source_meta_
    assert SourceName.MONDO in response.source_meta_
    assert SourceName.ONCOTREE in response.source_meta_


def test_service_meta(query_handler):
    """Test service meta info in response."""
    test_query = "glioma"

    response = query_handler.search(test_query)
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version >= "0.2.0"
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == 'https://github.com/cancervariants/disease-normalization'  # noqa: E501

    response = query_handler.normalize(test_query)
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version >= "0.2.0"
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == 'https://github.com/cancervariants/disease-normalization'  # noqa: E501

    response = query_handler.search('this-will-not-normalize')
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version >= "0.2.0"
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == 'https://github.com/cancervariants/disease-normalization'  # noqa: E501

    response = query_handler.normalize('this-will-not-normalize')
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version >= "0.2.0"
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == 'https://github.com/cancervariants/disease-normalization'  # noqa: E501
