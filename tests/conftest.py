"""Pytest test config tools."""

import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from disease.config import get_config
from disease.database.database import AWS_ENV_VAR_NAME, AbstractDatabase, create_db
from disease.etl.base import Base
from disease.query import QueryHandler
from disease.schemas import (
    Disease,
    MatchType,
    RecordType,
    RefType,
    SourceMeta,
    SourceName,
    SourceSearchMatches,
)

_logger = logging.getLogger(__name__)


def pytest_collection_modifyitems(items):
    """Modify test items in place to ensure test modules run in a given order.

    When creating new test modules, be sure to add them here.
    """
    module_order = [
        "test_schemas",
        "test_mondo",
        "test_do",
        "test_ncit",
        "test_omim",
        "test_oncotree",
        "test_merge",
        "test_database",
        "test_query",
        "test_api",
        "test_emit_warnings",
        "test_utils",
    ]
    # remember to add new test modules to the order constant:
    assert len(module_order) == len(list(Path(__file__).parent.rglob("test_*.py")))
    items.sort(key=lambda i: module_order.index(i.module.__name__))


def pytest_addoption(parser):
    """Add custom commands to pytest invocation.
    See https://docs.pytest.org/en/7.1.x/reference/reference.html#parser
    """
    parser.addoption(
        "--verbose-logs",
        action="store_true",
        default=False,
        help="show noisy module logs",
    )


def pytest_configure(config):
    """Configure pytest setup."""
    if not config.getoption("--verbose-logs"):
        logging.getLogger("botocore").setLevel(logging.ERROR)
        logging.getLogger("boto3").setLevel(logging.ERROR)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide Path instance pointing to test data directory"""
    return Path(__file__).parent / "data"


def pytest_sessionstart():
    """Wipe DB before testing if in test environment."""
    if get_config().test:
        if os.environ.get(AWS_ENV_VAR_NAME):
            msg = f"Cannot have both DISEASE_NORM_TEST and {AWS_ENV_VAR_NAME} set."
            raise AssertionError(msg)
        db = create_db()
        db.drop_db()
        db.initialize_db()


@pytest.fixture(scope="session")
def is_test_env():
    """If true, currently in test environment (i.e. okay to overwrite DB). Downstream
    users should also make sure to check if in a production environment.

    Provided here to be accessible directly within test modules.
    """
    return get_config().test


@pytest.fixture(scope="module")
def database():
    """Provide a database instance to be used by tests."""
    db = create_db()
    yield db
    db.close_connection()


@pytest.fixture(scope="module")
def test_source(database: AbstractDatabase, is_test_env: bool, test_data_dir: Path):
    """Provide query endpoint for testing sources. If DISEASE_NORM_TEST is set, will try to
    load DB from test data.

    :param database: test database instance
    :param is_test_env: if true, load from test data
    :return: factory function that takes an ETL class instance and returns a query
    endpoint.
    """

    def test_source_factory(EtlClass: Base):  # noqa: N803
        if is_test_env:
            _logger.debug("Reloading DB with data from %s", test_data_dir)
            test_class = EtlClass(database, test_data_dir / EtlClass.__name__.lower())
            test_class.perform_etl(use_existing=True)

        class QueryGetter:
            def __init__(self):
                self.query_handler = QueryHandler(database)
                self._src_name = EtlClass.__name__

            def search(self, query_str: str):
                resp = self.query_handler.search(query_str, incl=self._src_name)
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

    assert (actual.oncologic_disease is None) == (fixt.oncologic_disease is None)
    if (actual.oncologic_disease is not None) and (fixt.oncologic_disease is not None):
        assert actual.oncologic_disease == fixt.oncologic_disease


@pytest.fixture(scope="session")
def compare_records():
    """Provide record comparison function"""
    return _compare_records


def _compare_response(
    response: SourceSearchMatches,
    match_type: MatchType,
    fixture: Disease | None = None,
    fixture_list: list[Disease] | None = None,
    num_records: int = 0,
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
        pytest.fail("Args provided for both `fixture` and `fixture_list`")
    if not fixture and not fixture_list:
        pytest.fail("Must pass 1 of {fixture, fixture_list}")
    if fixture and num_records:
        pytest.fail("`num_records` should only be given with `fixture_list`.")

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
            raise AssertionError  # test fixture not found in response


@pytest.fixture(scope="session")
def compare_response():
    """Provide response comparison function"""
    return _compare_response


@pytest.fixture(scope="session")
def null_database_class():
    """Quote-unquote 'in-memory database' used like a mock for testing.

    Parameters for specific methods enabled as needed. See `tests/unit/test_utils.py`
    for example usage.
    """

    class _Database(AbstractDatabase):
        def __init__(self, db_url: str | None = None, **db_args) -> None:  # noqa: ARG002
            self._get_all_records_values = db_args.get("get_all_records", {})

        def list_tables(self) -> list[str]:
            raise NotImplementedError

        def drop_db(self) -> None:
            raise NotImplementedError

        def check_schema_initialized(self) -> bool:
            raise NotImplementedError

        def check_tables_populated(self) -> bool:
            raise NotImplementedError

        def initialize_db(self) -> None:
            raise NotImplementedError

        def get_source_metadata(self, src_name: str | SourceName) -> SourceMeta | None:
            raise NotImplementedError

        def get_record_by_id(
            self, concept_id: str, case_sensitive: bool = True, merge: bool = False
        ) -> dict | None:
            raise NotImplementedError

        def get_refs_by_type(self, search_term: str, ref_type: RefType) -> list[str]:
            raise NotImplementedError

        def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]:
            raise NotImplementedError

        def get_all_records(
            self, record_type: RecordType
        ) -> Generator[dict, None, None]:
            yield from self._get_all_records_values[record_type]

        def add_source_metadata(self, src_name: SourceName, meta: SourceMeta) -> None:
            raise NotImplementedError

        def add_record(self, record: dict, src_name: SourceName) -> None:
            raise NotImplementedError

        def add_merged_record(self, record: dict) -> None:
            raise NotImplementedError

        def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
            raise NotImplementedError

        def delete_normalized_concepts(self) -> None:
            raise NotImplementedError

        def delete_source(self, src_name: SourceName) -> None:
            raise NotImplementedError

        def complete_write_transaction(self) -> None:
            raise NotImplementedError

        def close_connection(self) -> None:
            raise NotImplementedError

        def load_from_remote(self, url: str | None = None) -> None:
            raise NotImplementedError

        def export_db(self, export_location: Path) -> None:
            raise NotImplementedError

    return _Database
