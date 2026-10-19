# ruff: noqa: ARG002
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from ga4gh.core.models import MappableConcept
from ga4gh.va_spec.base import DataSet

from disease.database import AbstractDatabase
from disease.schemas import RecordType, RefType, SourceMeta, SourceName


class NullDatabase(AbstractDatabase):
    def __init__(self, db_url: str | None = None, **db_args) -> None:
        self._added_records: dict[str, MappableConcept] = {}
        self._added_sources: dict[SourceName, MappableConcept] = {}
        self._added_merged_records: dict[str, MappableConcept] = {}
        self._updated_merge_refs: dict[str, str] = {}
        self._delete_merge_called = False
        self._delete_source_calls = set()
        self._get_all_records_values = db_args.get("get_all_records", {})

    def list_tables(self) -> list[str]: ...

    def drop_db(self) -> None: ...

    def check_schema_initialized(self) -> bool: ...

    def check_tables_populated(self) -> bool: ...

    def initialize_db(self) -> None: ...

    def get_source_metadata(self, src_name: str | SourceName) -> SourceMeta | None: ...

    def get_record_by_id(
        self, concept_id: str, case_sensitive: bool = True, merge: bool = False
    ) -> dict | None: ...

    def get_refs_by_type(self, search_term: str, ref_type: RefType) -> list[str]: ...

    def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]: ...

    def get_all_records(self, record_type: RecordType) -> Generator[dict, None, None]:
        yield from self._get_all_records_values[record_type]

    def add_source_metadata(self, source_name: SourceName, source: DataSet) -> None:
        """Add new source metadata entry.

        :param source_name: name of source
        :param source: source dataset description
        :raise DatabaseWriteException: if write fails
        """
        self._added_sources[source_name] = source

    def add_record(self, disease: MappableConcept, src_name: SourceName) -> None:
        """Add new record to database.

        :param disease: disease record to upload
        :param src_name: name of source for record.
        """
        self._added_records[disease.id] = disease

    def add_merged_record(self, record: MappableConcept) -> None:
        """Add merged record to database.

        :param record: merged record to add
        """
        self._added_merged_records[record.id] = record

    def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
        """Update the merged record reference of an individual record to a new value.

        :param concept_id: record to update
        :param merge_ref: new ref value
        :raise DatabaseWriteException: if attempting to update non-existent record
        """
        self._updated_merge_refs[concept_id] = merge_ref

    def delete_normalized_concepts(self) -> None:
        """Remove merged records from the database. Use when performing a new update
        of normalized data.

        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """
        self._delete_merge_called = True

    def delete_source(self, src_name: SourceName) -> None:
        """Delete all data for a source. Use when updating source data.

        :param src_name: name of source to delete
        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """
        self._delete_source_calls.add(src_name)

    def complete_write_transaction(self) -> None: ...

    def close_connection(self) -> None: ...

    def load_from_remote(self, url: str | None = None) -> None: ...

    def export_db(self, output_directory: Path) -> None: ...


@pytest.fixture
def mock_etl_db() -> NullDatabase:
    return NullDatabase()
