"""Pytest tst config tools."""

import json
import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from ga4gh.core.models import (
    MappableConcept,
)
from ga4gh.va_spec.base import DataSet

from disease.config import get_config
from disease.database.database import AWS_ENV_VAR_NAME, AbstractDatabase, create_db
from disease.etl.base import Base
from disease.query import QueryHandler
from disease.schemas import (
    RecordType,
    RefType,
    SourceMeta,
    SourceName,
    mapcon_to_disease,
)

_logger = logging.getLogger(__name__)


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


@pytest.fixture
def mock_db_class():
    """Provide mock db class definition

    Instantiate
    """

    class NullDatabase(AbstractDatabase):
        def __init__(self, db_url: str | None = None, **db_args) -> None:  # noqa: ARG002
            self._get_all_records_values = db_args.get("get_all_records", {})
            self._get_record_by_id_values = db_args.get("get_record_by_id", {})
            self._added_records: dict[str, MappableConcept] = {}
            self._added_sources: dict[SourceName, MappableConcept] = {}
            self._added_merged_records: dict[str, MappableConcept] = {}
            self._updated_merge_refs: dict[str, str] = {}
            self._delete_merge_called = False
            self._delete_source_calls = set()

        def list_tables(self) -> list[str]: ...

        def drop_db(self) -> None: ...

        def check_schema_initialized(self) -> bool: ...

        def check_tables_populated(self) -> bool: ...

        def initialize_db(self) -> None: ...

        def get_source_metadata(
            self, src_name: str | SourceName
        ) -> SourceMeta | None: ...

        def get_record_by_id(
            self,
            concept_id: str,
            case_sensitive: bool = True,
            merge: bool = False,  # noqa: ARG002
        ) -> dict | None:
            key = concept_id
            if case_sensitive:
                key = key.lower()
                response_map = {
                    k.lower(): v for k, v in self._get_record_by_id_values.items()
                }
            else:
                response_map = self._get_record_by_id_values
            result = response_map.get(key)
            if not result:
                return None
            return mapcon_to_disease(result).model_dump()

        def get_refs_by_type(
            self, search_term: str, ref_type: RefType
        ) -> list[str]: ...

        def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]: ...

        def get_all_records(
            self, record_type: RecordType
        ) -> Generator[dict, None, None]:
            yield from self._get_all_records_values[record_type]

        def add_source_metadata(self, source_name: SourceName, source: DataSet) -> None:
            self._added_sources[source_name] = source

        def add_record(self, disease: MappableConcept, src_name: SourceName) -> None:  # noqa: ARG002
            self._added_records[disease.id] = disease

        def add_merged_record(self, record: MappableConcept) -> None:
            self._added_merged_records[record.id] = record

        def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
            self._updated_merge_refs[concept_id] = merge_ref

        def delete_normalized_concepts(self) -> None:
            self._delete_merge_called = True

        def delete_source(self, src_name: SourceName) -> None:
            self._delete_source_calls.add(src_name)

        def complete_write_transaction(self) -> None: ...

        def close_connection(self) -> None: ...

        def load_from_remote(self, url: str | None = None) -> None: ...

        def export_db(self, output_directory: Path) -> None: ...

    return NullDatabase


@pytest.fixture
def diseases(test_data_dir: Path) -> dict[str, MappableConcept]:
    with (test_data_dir / "diseases.json").open() as f:
        data = json.load(f)
    return {k: MappableConcept(**v) for k, v in data.items()}


@pytest.fixture
def merged_diseases(test_data_dir: Path) -> dict[str, MappableConcept]:
    with (test_data_dir / "merged_diseases.json").open() as f:
        data = json.load(f)
    return {k: MappableConcept(**v) for k, v in data.items()}


@pytest.fixture
def merged_groups() -> dict[str, list[str]]:
    return {
        "normalize.disease.ncit:C167370": ["ncit:C167370"],
        "normalize.disease.ncit:C3270": [
            "ncit:C3270",
            "mondo:0005072",
            "DOID:769",
            "oncotree:NBL",
        ],
        "normalize.disease.ncit:C2926": [
            "ncit:C2926",
            "mondo:0005233",
            "DOID:3908",
            "oncotree:NSCLC",
        ],
        "normalize.disease.ncit:C35424": ["ncit:C35424", "mondo:0002083", "DOID:1703"],
        "normalize.disease.ncit:C8091": ["ncit:C8091", "mondo:0003587", "DOID:5695"],
        "normalize.disease.ncit:C9012": ["ncit:C9012", "mondo:0004099", "DOID:7079"],
        "normalize.disease.mondo:0010648": ["mondo:0010648", "MIM:309200"],
    }


@pytest.fixture
def sources(test_data_dir: Path) -> dict[str, DataSet]:
    with (test_data_dir / "sources.json").open() as f:
        data = json.load(f)
    return {SourceName(k): DataSet(**v) for k, v in data.items()}


@pytest.fixture
def db() -> AbstractDatabase:
    """A real live db instance (gets overwritten immediately)"""
    db_instance = create_db()
    try:
        db_instance.drop_db()
        db_instance.initialize_db()
        yield db_instance
    finally:
        db_instance.drop_db()
