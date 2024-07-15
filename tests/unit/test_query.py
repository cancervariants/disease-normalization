"""Test the disease querying method."""

from datetime import datetime

import pytest
from ga4gh.core import domain_models

from disease.query import InvalidParameterException, QueryHandler
from disease.schemas import MatchType, SourceName


@pytest.fixture(scope="module")
def query_handler(database):
    """Build query handler test fixture"""
    return QueryHandler(database)


@pytest.fixture(scope="module")
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return domain_models.Disease(
        type="Disease",
        id="normalize.disease.ncit:C3270",
        label="Neuroblastoma",
        mappings=[
            {
                "coding": {"code": "0005072", "system": "mondo"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "NBL", "system": "oncotree"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "769", "system": "doid"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "C0027819", "system": "umls"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "9500/3", "system": "icdo"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "0000621", "system": "efo"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "7185", "system": "gard"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "D009447", "system": "mesh"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "635", "system": "orphanet"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "C2751421", "system": "umls"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "CN205405", "system": "umls"},
                "relation": "relatedMatch",
            },
        ],
        alternativeLabels=[
            "NB",
            "neuroblastoma",
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "Neuroblastoma, NOS",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma (NBL)",
            "neural Crest tumor, malignant",
            "neuroblastoma, malignant",
        ],
    )


@pytest.fixture(scope="module")
def skin_myo():
    """Create a test fixture for skin myopithelioma"""
    return domain_models.Disease(
        type="Disease",
        id="normalize.disease.ncit:C167370",
        label="Skin Myoepithelioma",
        alternativeLabels=["Cutaneous Myoepithelioma"],
    )


@pytest.fixture(scope="module")
def mafd2():
    """Create a test fixture for major affective disorder 2. Query should not
    include a "pediatric_disease" Extension object.
    """
    return domain_models.Disease(
        type="Disease",
        id="normalize.disease.mondo:0010648",
        label="major affective disorder 2",
        alternativeLabels=[
            "MAFD2",
            "MDI",
            "MDX",
            "MANIC-DEPRESSIVE ILLNESS",
            "BPAD",
            "MAFD2",
            "BIPOLAR AFFECTIVE DISORDER",
            "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
            "major affective disorder 2, X-linked dominant",
            "MAJOR affective disorder 2",
            "bipolar affective disorder",
            "major affective disorder 2",
            "manic-depressive illness",
            "manic-depressive psychosis, X-linked",
        ],
        mappings=[
            {
                "coding": {"code": "309200", "system": "omim"},
                "relation": "relatedMatch",
            },
            {
                "coding": {"code": "C564108", "system": "mesh"},
                "relation": "relatedMatch",
            },
        ],
    )


def compare_disease(actual, fixture):
    """Verify correctness of returned Disease core object against test fixture."""
    assert actual.normalized_id == fixture.id.split("normalize.disease.")[-1]
    actual = actual.disease
    actual_keys = actual.model_dump(exclude_none=True).keys()
    fixture_keys = fixture.model_dump(exclude_none=True).keys()
    assert actual_keys == fixture_keys
    assert actual.id == fixture.id
    assert actual.type == fixture.type
    assert actual.label == fixture.label

    assert bool(actual.mappings) == bool(fixture.mappings)
    if actual.mappings:
        no_matches = []
        for actual_mapping in actual.mappings:
            match = None
            for fixture_mapping in fixture.mappings:
                if actual_mapping == fixture_mapping:
                    match = actual_mapping
                    break
            if not match:
                no_matches.append(actual_mapping)
        assert no_matches == [], no_matches
        assert len(actual.mappings) == len(fixture.mappings)

    assert bool(actual.alternativeLabels) == bool(fixture.alternativeLabels)
    if actual.alternativeLabels:
        assert set(actual.alternativeLabels) == set(fixture.alternativeLabels)

    def get_extension(extensions, name):
        matches = [e for e in extensions if e.name == name]
        if len(matches) > 1:
            raise AssertionError
        if len(matches) == 1:
            return matches[0]
        return None

    assert bool(actual.extensions) == bool(fixture.extensions)
    if actual.extensions:
        ext_actual = actual.extensions
        ext_fixture = fixture.extensions

        ped_actual = get_extension(ext_actual, "pediatric_disease")
        ped_fixture = get_extension(ext_fixture, "pediatric_disease")
        assert (ped_actual is None) == (ped_fixture is None)
        if ped_actual and ped_fixture:
            assert set(ped_actual.value) == set(ped_fixture.value)
            assert ped_actual.value


def test_query(query_handler):
    """Test that query returns properly-structured response."""
    resp = query_handler.search("Neuroblastoma")
    assert resp.query == "Neuroblastoma"
    matches = resp.source_matches
    assert isinstance(matches, dict)
    assert len(matches) == 5
    ncit = matches["NCIt"]
    assert len(ncit.records) == 1
    ncit_record = ncit.records[0]
    assert ncit_record.label == "Neuroblastoma"


def test_query_specify_query_handlers(query_handler):
    """Test inclusion and exclusion of sources in query."""
    # test full inclusion
    sources = "ncit,mondo,do,oncotree,omim"
    resp = query_handler.search("Neuroblastoma", incl=sources, excl="")
    matches = resp.source_matches
    assert len(matches) == 5
    assert SourceName.NCIT in matches
    assert SourceName.MONDO in matches
    assert SourceName.DO in matches
    assert SourceName.ONCOTREE in matches
    assert SourceName.OMIM in matches

    # test full exclusion
    resp = query_handler.search("Neuroblastoma", excl=sources)
    matches = resp.source_matches
    assert len(matches) == 0

    # test case insensitive
    resp = query_handler.search("Neuroblastoma", excl="NCIt")
    matches = resp.source_matches
    assert SourceName.NCIT not in matches
    resp = query_handler.search("Neuroblastoma", incl="nCiT")
    matches = resp.source_matches
    assert SourceName.NCIT in matches

    # test error on invalid source names
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search("Neuroblastoma", incl="nct")

    # test error for supplying both incl and excl args
    with pytest.raises(InvalidParameterException):
        resp = query_handler.search("Neuroblastoma", incl="mondo", excl="ncit")


def test_normalize_query(query_handler, neuroblastoma, mafd2):
    """Test that normalized endpoint correctly resolves queries, and utilizes
    the VOD schema.
    """
    response = query_handler.normalize("Neuroblastoma")
    assert response.match_type == MatchType.LABEL
    assert response.warnings is None
    compare_disease(response, neuroblastoma)
    assert len(response.source_meta_) == 4
    assert SourceName.NCIT in response.source_meta_
    assert SourceName.DO in response.source_meta_
    assert SourceName.MONDO in response.source_meta_
    assert SourceName.ONCOTREE in response.source_meta_

    response = query_handler.normalize("MAFD2")
    assert response.match_type == MatchType.ALIAS
    assert response.warnings is None
    compare_disease(response, mafd2)
    assert len(response.source_meta_) == 2
    assert SourceName.MONDO in response.source_meta_


def test_normalize_non_mondo(query_handler, skin_myo, neuroblastoma):
    """Test that normalize endpoint returns records not in Mondo groups."""
    response = query_handler.normalize("Skin Myoepithelioma")
    assert response.match_type == MatchType.LABEL
    assert len(response.source_meta_) == 1
    compare_disease(response, skin_myo)
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize("Cutaneous Myoepithelioma")
    assert response.match_type == MatchType.ALIAS
    assert len(response.source_meta_) == 1
    compare_disease(response, skin_myo)
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize("orphanet:635")
    assert response.match_type == MatchType.XREF
    assert len(response.source_meta_) == 4
    compare_disease(response, neuroblastoma)
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
    assert service_meta.version
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == "https://github.com/cancervariants/disease-normalization"

    response = query_handler.normalize(test_query)
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == "https://github.com/cancervariants/disease-normalization"

    response = query_handler.search("this-will-not-normalize")
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == "https://github.com/cancervariants/disease-normalization"

    response = query_handler.normalize("this-will-not-normalize")
    service_meta = response.service_meta_
    assert service_meta.name == "disease-normalizer"
    assert service_meta.version
    assert isinstance(service_meta.response_datetime, datetime)
    assert service_meta.url == "https://github.com/cancervariants/disease-normalization"
