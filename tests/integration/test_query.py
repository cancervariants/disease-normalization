"""Test end-to-end results of data ingest to querying"""

from datetime import datetime

import pytest
from deepdiff import DeepDiff
from ga4gh.core.models import MappableConcept

from disease.database import AbstractDatabase
from disease.query import InvalidParameterException, QueryHandler
from disease.schemas import MatchType, SourceName


@pytest.fixture(scope="module")
def query_handler(populated_db: AbstractDatabase) -> QueryHandler:
    """Build query handler test fixture"""
    return QueryHandler(populated_db)


def compare_disease(actual, fixture):
    """Verify correctness of returned Disease core object against test fixture."""
    actual = actual.disease
    diff = DeepDiff(fixture, actual, ignore_order=True)
    assert diff == {}, diff.pretty()


def test_query(query_handler: QueryHandler):
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


def test_query_specify_query_handlers(query_handler: QueryHandler):
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


def test_normalize_query(
    query_handler: QueryHandler, merged_diseases: dict[str, MappableConcept]
):
    """Test that normalized endpoint correctly resolves queries, and utilizes
    the VOD schema.
    """
    response = query_handler.normalize("Neuroblastoma")
    assert response.match_type == MatchType.LABEL
    assert response.warnings is None
    compare_disease(response, merged_diseases["normalize.disease.ncit:C3270"])
    assert len(response.source_meta_) == 4
    assert SourceName.NCIT in response.source_meta_
    assert SourceName.DO in response.source_meta_
    assert SourceName.MONDO in response.source_meta_
    assert SourceName.ONCOTREE in response.source_meta_

    response = query_handler.normalize("MAFD2")
    assert response.match_type == MatchType.ALIAS
    assert response.warnings is None
    compare_disease(response, merged_diseases["normalize.disease.mondo:0010648"])
    assert len(response.source_meta_) == 2
    assert SourceName.MONDO in response.source_meta_


def test_normalize_non_mondo(
    query_handler: QueryHandler, merged_diseases: dict[str, MappableConcept]
):
    """Test that normalize endpoint returns records not in Mondo groups."""
    response = query_handler.normalize("Skin Myoepithelioma")
    assert response.match_type == MatchType.LABEL
    assert len(response.source_meta_) == 1
    compare_disease(response, merged_diseases["normalize.disease.ncit:C167370"])
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize("Cutaneous Myoepithelioma")
    assert response.match_type == MatchType.ALIAS
    assert len(response.source_meta_) == 1
    compare_disease(response, merged_diseases["normalize.disease.ncit:C167370"])
    assert SourceName.NCIT in response.source_meta_

    response = query_handler.normalize("orphanet:635")
    assert response.match_type == MatchType.XREF
    assert len(response.source_meta_) == 4
    compare_disease(response, merged_diseases["normalize.disease.ncit:C3270"])
    assert SourceName.NCIT in response.source_meta_
    assert SourceName.DO in response.source_meta_
    assert SourceName.MONDO in response.source_meta_
    assert SourceName.ONCOTREE in response.source_meta_


def test_service_meta(query_handler: QueryHandler):
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
