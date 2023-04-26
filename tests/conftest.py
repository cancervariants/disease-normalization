"""Pytest test config tools."""
import os
import tarfile
from typing import List, Optional
import pytest
from pathlib import Path
import logging

from disease.database import AWS_ENV_VAR_NAME, create_db
from disease.database.database import AbstractDatabase
from disease.etl.base import Base
from disease.query import QueryHandler
from disease.schemas import Disease, MatchType, MatchesKeyed, SourceName

_logger = logging.getLogger(__name__)


def pytest_collection_modifyitems(items):
    """Modify test items in place to ensure test modules run in a given order.
    When creating new test modules, be sure to add them here.
    """
    MODULE_ORDER = [
        "test_mondo",
        "test_do",
        "test_ncit",
        "test_omim",
        "test_oncotree",
        "test_merge",
        "test_database",
        "test_query",
        "test_emit_warnings",
    ]
    # remember to add new test modules to the order constant:
    assert len(MODULE_ORDER) == len(list(Path(__file__).parent.rglob("test_*.py")))
    items.sort(key=lambda i: MODULE_ORDER.index(i.module.__name__))


TEST_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA_DIRECTORY = TEST_ROOT / "tests" / "data"
IS_TEST_ENV = os.environ.get("DISEASE_TEST", "").lower() == "true"


def pytest_sessionstart():
    """Wipe DB before testing if in test environment."""
    if IS_TEST_ENV:
        if os.environ.get(AWS_ENV_VAR_NAME):
            assert False, f"Cannot have both DISEASE_TEST and {AWS_ENV_VAR_NAME} set."
        db = create_db()
        db.drop_db()
        db.initialize_db()


@pytest.fixture(scope="session")
def is_test_env():
    """If true, currently in test environment (i.e. okay to overwrite DB). Downstream
    users should also make sure to check if in a production environment.

    Provided here to be accessible directly within test modules.
    """
    return IS_TEST_ENV


@pytest.fixture(scope="module")
def database():
    """Provide a database instance to be used by tests."""
    db = create_db()
    yield db
    db.close_connection()


def decompress_mondo_tar():
    """Mondo fixture data was hard to subset down to a reasonably commmit-able size, so
    it's stored as a tarball instead. We'll need to decompress it.

    This method expects to find a single tarball in the test mondo directory. If
    there's already a decompressed OWL file there too, it won't do any redundant work.
    This does mean that you might have to manually delete your local copy of the OWL
    file if a new version of the tarfile is committed to the repo.
    """
    mondo_data_dir = TEST_DATA_DIRECTORY / "mondo"
    if len(list(mondo_data_dir.glob("mondo_*.owl"))) > 0:
        return
    tarball = list(mondo_data_dir.glob("fixture_mondo_*.owl.tar.gz"))[0]
    with tarfile.open(tarball, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".owl"):
                member.name = os.path.basename(member.name)
                tar.extract(member, path=mondo_data_dir)
                break
        else:
            raise FileNotFoundError("Unable to find compressed Mondo OWL file")


@pytest.fixture(scope="module")
def test_source(database: AbstractDatabase, is_test_env: bool):
    """Provide query endpoint for testing sources. If DISEASE_TEST is set, will try to
    load DB from test data.

    :param db: database fixture
    :return: factory function that takes an ETL class instance and returns a query
    endpoint.
    """
    def test_source_factory(EtlClass: Base):
        if is_test_env:
            _logger.debug(f"Reloading DB with data from {TEST_DATA_DIRECTORY}")
            test_class = EtlClass(database, TEST_DATA_DIRECTORY)  # type: ignore
            if EtlClass.__name__ == SourceName.MONDO:  # type: ignore
                decompress_mondo_tar()
            test_class.perform_etl(use_existing=True)

        class QueryGetter:

            def __init__(self):
                self.query_handler = QueryHandler(database)
                self._src_name = EtlClass.__name__  # type: ignore

            def search(self, query_str: str):
                resp = self.query_handler.search(
                    query_str, keyed=True, incl=self._src_name
                )
                return resp.source_matches[self._src_name]

        return QueryGetter()

    return test_source_factory


def _compare_records(actual: Disease, fixt: Disease):
    """Check that identity records are identical."""
    assert actual.concept_id == fixt.concept_id
    assert actual.label == fixt.label

    assert (actual.aliases is None) == (fixt.aliases is None)
    if (actual.aliases is not None) and (fixt.aliases is not None):
        assert set(actual.aliases) == set(fixt.aliases)

    assert (actual.xrefs is None) == (fixt.xrefs is None)
    if (actual.xrefs is not None) and (fixt.xrefs is not None):
        assert set(actual.xrefs) == set(fixt.xrefs)

    assert (actual.associated_with is None) == (fixt.associated_with is None)
    if (actual.associated_with is not None) and (fixt.associated_with is not None):
        assert set(actual.associated_with) == set(fixt.associated_with)

    assert (actual.pediatric_disease is None) == (fixt.pediatric_disease is None)
    if (actual.pediatric_disease is not None) and (fixt.pediatric_disease is not None):
        assert actual.pediatric_disease == fixt.pediatric_disease


@pytest.fixture(scope="session")
def compare_records():
    """Provide record comparison function"""
    return _compare_records


def _compare_response(
    response: MatchesKeyed, match_type: MatchType, fixture: Optional[Disease] = None,
    fixture_list: Optional[List[Disease]] = None, num_records: int = 0
):
    """Check that test response is correct. Only 1 of {fixture, fixture_list}
    should be passed as arguments. num_records should only be passed with fixture_list.

    :param Dict response: response object returned by QueryHandler
    :param MatchType match_type: expected match type
    :param Disease fixture: single Disease object to match response against
    :param List[Disease] fixture_list: multiple Disease objects to match response
        against
    :param int num_records: expected number of records in response. If not given, tests
        for number of fixture Diseases given (ie, 1 for single fixture and length of
        fixture_list otherwise)
    """
    if fixture and fixture_list:
        raise Exception("Args provided for both `fixture` and `fixture_list`")
    elif not fixture and not fixture_list:
        raise Exception("Must pass 1 of {fixture, fixture_list}")
    if fixture and num_records:
        raise Exception("`num_records` should only be given with `fixture_list`.")

    assert response.match_type == match_type
    if fixture:
        assert len(response.records) == 1
        _compare_records(response.records[0], fixture)
    elif fixture_list:
        if not num_records:
            assert len(response.records) == len(fixture_list)
        else:
            assert len(response.records) == num_records
        for fixt in fixture_list:
            for record in response.records:
                if fixt.concept_id == record.concept_id:
                    _compare_records(record, fixt)
                    break
            else:
                assert False  # test fixture not found in response


@pytest.fixture(scope="session")
def compare_response():
    """Provide response comparison function"""
    return _compare_response
