"""Provide PostgreSQL client."""

import atexit
import datetime
import logging
import os
import tarfile
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, ClassVar

import psycopg
import requests
from psycopg.errors import (
    DuplicateObject,
    DuplicateTable,
    UndefinedTable,
    UniqueViolation,
)

from disease.database import AbstractDatabase, DatabaseException, DatabaseWriteException
from disease.schemas import (
    DataLicenseAttributes,
    RecordType,
    RefType,
    SourceMeta,
    SourceName,
)

_logger = logging.getLogger()


SCRIPTS_DIR = Path(__file__).parent / "postgresql"


class PostgresDatabase(AbstractDatabase):
    """Disease Normalizer database client for PostgreSQL."""

    def __init__(self, db_url: str | None = None, **db_args) -> None:
        """Initialize Postgres connection.

        .. code-block:: pycon

           >>> from disease.database.postgresql import PostgresDatabase
           >>> db = PostgresDatabase(
           >>>     user="postgres",
           >>>     password="matthew_cannon2",
           >>>     db_name="disease_normalizer"
           >>> )

        :param db_url: libpq compliant database connection URI
        :Keyword Arguments:
            * user: Postgres username
            * password: Postgres password (optional or blank if unneeded)
            * db_name: name of database to connect to
        :raise DatabaseInitializationException: if initial setup fails
        """
        if db_url:
            conninfo = db_url
        elif "DISEASE_NORM_DB_URL" in os.environ:
            conninfo = os.environ["DISEASE_NORM_DB_URL"]
        else:
            user = db_args.get("user", "postgres")
            password = db_args.get("password", "")
            db_name = db_args.get("db_name", "disease_normalizer")
            if password:
                conninfo = f"dbname={db_name} user={user} password={password}"
            else:
                conninfo = f"dbname={db_name} user={user}"

        self.conn = psycopg.connect(conninfo)
        self.initialize_db()
        self._cached_sources: dict[str, SourceMeta] = {}

        atexit.register(self.close_connection)

    _list_tables_query = b"""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';
    """

    def list_tables(self) -> list[str]:
        """Return names of tables in database.

        :return: Table names in database
        """
        with self.conn.cursor() as cur:
            cur.execute(self._list_tables_query)
            tables = cur.fetchall()
        return [t[0] for t in tables]

    _drop_db_query = b"""
    DROP MATERIALIZED VIEW IF EXISTS record_lookup_view;
    DROP TABLE IF EXISTS
        disease_aliases,
        disease_associations,
        disease_concepts,
        disease_labels,
        disease_merged,
        disease_sources,
        disease_xrefs;
    """

    def drop_db(self) -> None:
        """Perform complete teardown of DB. Useful for quickly resetting all data or
        reconstructing after apparent schema error. If in a protected environment,
        require confirmation.

        :raise DatabaseWriteException: if called in a protected setting with
            confirmation silenced.
        """
        try:
            if not self._check_delete_okay():
                return
        except DatabaseWriteException:
            _logger.exception("Encountered DB write error when trying to drop DB")
            raise

        with self.conn.cursor() as cur:
            cur.execute(self._drop_db_query)
            self.conn.commit()
        _logger.info("Dropped all existing disease normalizer tables.")

    def check_schema_initialized(self) -> bool:
        """Check if database schema is properly initialized.

        :return: True if DB appears to be fully initialized, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute((SCRIPTS_DIR / "create_tables.sql").read_bytes())
        except DuplicateTable:
            self.conn.rollback()
        else:
            _logger.info("Disease table existence check failed.")
            self.conn.rollback()
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute((SCRIPTS_DIR / "add_fkeys.sql").read_bytes())
        except DuplicateObject:
            self.conn.rollback()
        else:
            _logger.info("Disease foreign key existence check failed.")
            self.conn.rollback()
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    (SCRIPTS_DIR / "create_record_lookup_view.sql").read_bytes()
                )
        except DuplicateTable:
            self.conn.rollback()
        else:
            _logger.info("Disease normalized view lookup failed.")
            self.conn.rollback()
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute((SCRIPTS_DIR / "add_indexes.sql").read_bytes())
        except DuplicateTable:
            self.conn.rollback()
        else:
            _logger.info("Disease indexes check failed.")
            self.conn.rollback()
            return False

        return True

    _check_sources_query = b"SELECT name FROM disease_sources;"
    _check_concepts_query = b"SELECT COUNT(1) FROM disease_concepts LIMIT 1;"
    _check_merged_query = b"SELECT COUNT(1) FROM disease_merged LIMIT 1;"

    def check_tables_populated(self) -> bool:
        """Perform rudimentary checks to see if tables are populated.
        Emphasis is on rudimentary -- if some fiendish element has deleted half of the
        disease aliases, this method won't pick it up. It just wants to see if a few
        critical tables have at least a small number of records.

        :return: True if queries successful, false if DB appears empty
        """
        with self.conn.cursor() as cur:
            cur.execute(self._check_sources_query)
            results = cur.fetchall()
        if len(results) < len(SourceName):
            _logger.info("Disease sources table is missing expected sources.")
            return False

        with self.conn.cursor() as cur:
            cur.execute(self._check_concepts_query)
            result = cur.fetchone()
        if not result or result[0] < 1:
            _logger.info("Disease records table is empty.")
            return False

        with self.conn.cursor() as cur:
            cur.execute(self._check_merged_query)
            result = cur.fetchone()
        if not result or result[0] < 1:
            _logger.info("Normalized disease records table is empty.")
            return False

        return True

    def initialize_db(self) -> None:
        """Check if DB is set up. If not, create tables/indexes/views."""
        if not self.check_schema_initialized():
            self.drop_db()
            self._create_tables()
            self._create_views()
            self._add_indexes()

    def _create_views(self) -> None:
        """Create materialized views."""
        create_view_query = (SCRIPTS_DIR / "create_record_lookup_view.sql").read_bytes()
        with self.conn.cursor() as cur:
            cur.execute(create_view_query)
            self.conn.commit()

    _refresh_views_query = b"REFRESH MATERIALIZED VIEW record_lookup_view;"

    def _refresh_views(self) -> None:
        """Update materialized views.

        Not responsible for ensuring existence of views. Calling functions should
        either check beforehand or catch psycopg.UndefinedTable.
        """
        with self.conn.cursor() as cur:
            cur.execute(self._refresh_views_query)
            self.conn.commit()

    def _add_fkeys(self) -> None:
        """Add fkey relationships."""
        add_fkey_query = (SCRIPTS_DIR / "add_fkeys.sql").read_bytes()
        with self.conn.cursor() as cur:
            cur.execute(add_fkey_query)
            self.conn.commit()

    def _drop_fkeys(self) -> None:
        """Drop fkey relationships."""
        drop_fkey_query = (SCRIPTS_DIR / "drop_fkeys.sql").read_bytes()
        with self.conn.cursor() as cur:
            cur.execute(drop_fkey_query)
            self.conn.commit()

    def _add_indexes(self) -> None:
        """Create core search indexes."""
        add_indexes_query = (SCRIPTS_DIR / "add_indexes.sql").read_bytes()
        with self.conn.cursor() as cur:
            cur.execute(add_indexes_query)
            self.conn.commit()

    def _drop_indexes(self) -> None:
        """Drop all custom indexes."""
        drop_indexes_query = (SCRIPTS_DIR / "drop_indexes.sql").read_bytes()
        with self.conn.cursor() as cur:
            cur.execute(drop_indexes_query)
            self.conn.commit()

    def _create_tables(self) -> None:
        """Create all tables, indexes, and views."""
        _logger.debug("Creating new disease normalizer tables.")
        tables_query = (SCRIPTS_DIR / "create_tables.sql").read_bytes()

        with self.conn.cursor() as cur:
            cur.execute(tables_query)
            self.conn.commit()

    _source_metadata_query = b"SELECT * FROM disease_sources WHERE name = %s;"

    def get_source_metadata(self, src_name: str | SourceName) -> SourceMeta | None:
        """Get license, versioning, data lookup, etc information for a source.

        :param src_name: name of the source to get data for
        :return: source metadata, if lookup is successful
        """
        if isinstance(src_name, SourceName):
            src_name = src_name.value

        if src_name in self._cached_sources:
            return self._cached_sources[src_name]

        with self.conn.cursor() as cur:
            cur.execute(self._source_metadata_query, [src_name])
            metadata_result = cur.fetchone()
            if not metadata_result:
                return None
            metadata = SourceMeta(
                data_license=metadata_result[1],
                data_license_url=metadata_result[2],
                version=metadata_result[3],
                data_url=metadata_result[4],
                rdp_url=metadata_result[5],
                data_license_attributes=DataLicenseAttributes(
                    non_commercial=metadata_result[6],
                    attribution=metadata_result[7],
                    share_alike=metadata_result[8],
                ),
            )
            self._cached_sources[src_name] = metadata
            return metadata

    _record_query = b"SELECT * FROM record_lookup_view WHERE lower(concept_id) = %s;"

    def _format_source_record(self, source_row: tuple) -> dict:
        """Restructure row from disease_concepts table as source record result object.

        :param source_row: result tuple from psycopg
        :return: reformatted dictionary keying disease properties to row values
        """
        disease_record = {
            "concept_id": source_row[0],
            "label": source_row[1],
            "aliases": source_row[2],
            "associated_with": source_row[3],
            "xrefs": source_row[4],
            "src_name": source_row[5],
            "merge_ref": source_row[6],
            "pediatric_disease": source_row[7],
            "oncologic_disease": source_row[8],
            "item_type": RecordType.IDENTITY.value,
        }
        return {k: v for k, v in disease_record.items() if v}

    def _get_record(self, concept_id: str) -> dict | None:
        """Retrieve non-merged record. The query is pretty different, so this method
        is broken out for PostgreSQL.

        :param concept_id: ID of concept to get
        :return: complete record object if successful
        """
        concept_id_param = concept_id.lower()

        with self.conn.cursor() as cur:
            cur.execute(self._record_query, [concept_id_param])
            result = cur.fetchone()
        if not result:
            return None

        return self._format_source_record(result)

    _merged_record_query = b"SELECT * FROM disease_merged WHERE lower(concept_id) = %s;"

    def _format_merged_record(self, merged_row: tuple) -> dict:
        """Restructure row from disease_merged table as normalized result object.

        :param merged_row: result tuple from psycopg
        :return: reformatted dictionary keying normalized disease properties to row values
        """
        merged_record = {
            "concept_id": merged_row[0],
            "label": merged_row[1],
            "aliases": merged_row[2],
            "associated_with": merged_row[3],
            "xrefs": merged_row[4],
            "pediatric_disease": merged_row[5],
            "oncologic_disease": merged_row[6],
            "item_type": RecordType.MERGER.value,
        }
        return {k: v for k, v in merged_record.items() if v}

    def _get_merged_record(self, concept_id: str) -> dict | None:
        """Retrieve normalized record from DB.

        :param concept_id: normalized ID for the merged record
        :return: normalized record if successful
        """
        concept_id = concept_id.lower()
        with self.conn.cursor() as cur:
            cur.execute(self._merged_record_query, [concept_id])
            result = cur.fetchone()
        if not result:
            return None

        return self._format_merged_record(result)

    def get_record_by_id(
        self,
        concept_id: str,
        case_sensitive: bool = True,  # noqa: ARG002
        merge: bool = False,
    ) -> dict | None:
        """Fetch record corresponding to provided concept ID

        :param str concept_id: concept ID for disease record
        :param bool case_sensitive: not used by this implementation -- lookups use
           case-insensitive index
        :param bool merge: if true, look for merged record; look for identity record
           otherwise.
        :return: complete disease record, if match is found; None otherwise
        """
        if merge:
            return self._get_merged_record(concept_id)
        return self._get_record(concept_id)

    _ref_types_query: ClassVar[dict] = {
        RefType.LABEL: b"SELECT concept_id FROM disease_labels WHERE lower(label) = %s;",
        RefType.ALIASES: b"SELECT concept_id FROM disease_aliases WHERE lower(alias) = %s;",
        RefType.XREFS: "SELECT concept_id FROM disease_xrefs WHERE lower(xref) = %s;",
        RefType.ASSOCIATED_WITH: "SELECT concept_id FROM disease_associations WHERE lower(associated_with) = %s;",
    }

    def get_refs_by_type(self, search_term: str, ref_type: RefType) -> list[str]:
        """Retrieve concept IDs for records matching the user's query. Other methods
        are responsible for actually retrieving full records.

        :param search_term: string to match against
        :param ref_type: type of match to look for.
        :return: list of associated concept IDs. Empty if lookup fails.
        """
        query = self._ref_types_query.get(ref_type)
        if not query:
            msg = "invalid reference type"
            raise ValueError(msg)

        with self.conn.cursor() as cur:
            cur.execute(query, (search_term.lower(),))
            concept_ids = cur.fetchall()
        if concept_ids:
            return [i[0] for i in concept_ids]
        return []

    _source_ids_query = b"""
    SELECT concept_id FROM disease_concepts dc
    LEFT JOIN disease_sources ds ON ds.name = dc.source
    WHERE ds.name = %s;
    """
    _all_ids_query = b"SELECT concept_id FROM disease_concepts;"

    def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]:
        """Retrieve concept IDs for use in generating normalized records.

        :param source: optionally, just get all IDs for a specific source
        :return: Set of concept IDs as strings.
        """
        if source is not None:
            ids_query = self._source_ids_query
        else:
            ids_query = self._all_ids_query
        with self.conn.cursor() as cur:
            if source is None:
                cur.execute(ids_query)
            else:
                cur.execute(ids_query, (source,))
            ids_tuple = cur.fetchall()
        return {i[0] for i in ids_tuple}

    _get_all_normalized_records_query = b"SELECT * FROM disease_merged;"
    _get_all_unmerged_source_records_query = (
        b"SELECT * FROM record_lookup_view WHERE merge_ref IS NULL;"
    )
    _get_all_source_records_query = b"SELECT * FROM record_lookup_view;"

    def get_all_records(self, record_type: RecordType) -> Generator[dict, None, None]:
        """Retrieve all source or normalized records. Either return all source records,
        or all records that qualify as "normalized" (i.e., merged groups + source
        records that are otherwise ungrouped).

        For example,

        .. code-block:: pycon

           >>> from disease.database import create_db
           >>> from disease.schemas import RecordType
           >>> db = create_db()
           >>> for record in db.get_all_records(RecordType.MERGER):
           >>>     pass  # do something

        Unlike DynamoDB, merged records are stored in a separate table from source
        records. As a result, when fetching all normalized records, merged records are
        return first, and iteration continues with all source records that don't
        belong to a normalized concept group.

        :param record_type: type of result to return
        :return: Generator that lazily provides records as they are retrieved
        """
        batch_size = 500

        if record_type == RecordType.MERGER:
            with self.conn.cursor() as cur:
                results = cur.execute(self._get_all_normalized_records_query)
                fetched = results.fetchmany(batch_size)
                while fetched:
                    for row in fetched:
                        yield self._format_merged_record(row)
                    fetched = results.fetchmany(batch_size)
            with self.conn.cursor() as cur:
                results = cur.execute(self._get_all_unmerged_source_records_query)
                fetched = results.fetchmany(batch_size)
                while fetched:
                    for result in fetched:
                        yield self._format_source_record(result)
                    fetched = results.fetchmany(batch_size)
        else:
            with self.conn.cursor() as cur:
                results = cur.execute(self._get_all_source_records_query)
                fetched = results.fetchmany(batch_size)
                while fetched:
                    for result in fetched:
                        yield self._format_source_record(result)
                    fetched = results.fetchmany(batch_size)

    _add_source_metadata_query = b"""
    INSERT INTO disease_sources(
        name, data_license, data_license_url, version, data_url, rdp_url,
        data_license_nc, data_license_attr, data_license_sa
    )
    VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s );
    """

    def add_source_metadata(self, src_name: SourceName, meta: SourceMeta) -> None:
        """Add new source metadata entry.

        :param src_name: name of source
        :param meta: known source attributes
        :raise DatabaseWriteException: if write fails
        """
        with self.conn.cursor() as cur:
            cur.execute(
                self._add_source_metadata_query,
                [
                    src_name.value,
                    meta.data_license,
                    meta.data_license_url,
                    meta.version,
                    meta.data_url,
                    meta.rdp_url,
                    meta.data_license_attributes.non_commercial,
                    meta.data_license_attributes.attribution,
                    meta.data_license_attributes.share_alike,
                ],
            )
        self.conn.commit()

    _add_record_query = b"""
        INSERT INTO disease_concepts (concept_id, source, pediatric_disease, oncologic_disease)
        VALUES (%s, %s, %s, %s);
    """
    _insert_label_query = (
        b"INSERT INTO disease_labels (label, concept_id) VALUES (%s, %s)"
    )
    _insert_alias_query = (
        b"INSERT INTO disease_aliases (alias, concept_id) VALUES (%s, %s)"
    )
    _insert_xref_query = b"INSERT INTO disease_xrefs (xref, concept_id) VALUES (%s, %s)"
    _insert_assoc_query = b"INSERT INTO disease_associations (associated_with, concept_id) VALUES (%s, %s)"

    def add_record(self, record: dict, src_name: SourceName) -> None:
        """Add new record to database.

        :param record: record to upload
        :param src_name: name of source for record. Not used by PostgreSQL instance.
        """
        concept_id = record["concept_id"]
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    self._add_record_query,
                    [
                        concept_id,
                        src_name.value,
                        record.get("pediatric_disease"),
                        record.get("oncologic_disease"),
                    ],
                )
                cur.execute(self._insert_label_query, [record["label"], concept_id])
                for a in record.get("aliases", []):
                    cur.execute(self._insert_alias_query, [a, concept_id])
                for x in record.get("xrefs", []):
                    cur.execute(self._insert_xref_query, [x, concept_id])
                for a in record.get("associated_with", []):
                    cur.execute(self._insert_assoc_query, [a, concept_id])
                self.conn.commit()
            except UniqueViolation:
                _logger.error("Record with ID %s already exists", concept_id)  # noqa: TRY400
                self.conn.rollback()

    _add_merged_record_query = b"""
    INSERT INTO disease_merged (
        concept_id, label, aliases, associated_with, xrefs, pediatric_disease, oncologic_disease
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    def add_merged_record(self, record: dict) -> None:
        """Add merged record to database.

        :param record: merged record to add
        """
        with self.conn.cursor() as cur:
            cur.execute(
                self._add_merged_record_query,
                [
                    record["concept_id"],
                    record["label"],
                    record.get("aliases"),
                    record.get("associated_with"),
                    record.get("xrefs"),
                    record.get("pediatric_disease"),
                    record.get("oncologic_disease"),
                ],
            )
            self.conn.commit()

    _update_merge_ref_query = b"""
    UPDATE disease_concepts
    SET merge_ref = %(merge_ref)s
    WHERE concept_id = %(concept_id)s;
    """

    def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
        """Update the merged record reference of an individual record to a new value.

        :param concept_id: record to update
        :param merge_ref: new ref value
        :raise DatabaseWriteException: if attempting to update non-existent record
        """
        with self.conn.cursor() as cur:
            cur.execute(
                self._update_merge_ref_query,
                {"merge_ref": merge_ref, "concept_id": concept_id},
            )
            row_count = cur.rowcount
            self.conn.commit()

        # UPDATE will fail silently unless we check the # of affected rows
        if row_count < 1:
            msg = f"No such record exists for primary key {concept_id}"
            raise DatabaseWriteException(msg)

    def delete_normalized_concepts(self) -> None:
        """Remove merged records from the database. Use when performing a new update
        of normalized data.

        It would be faster to drop the entire table and do a cascading delete onto the
        merge_ref column in disease_concepts, but that requires an exclusive access lock
        on the DB, which can be annoying (ie you couldn't have multiple processes
        accessing it, or PgAdmin, etc...). Instead, we'll take down each merge table
        dependency and rebuild afterwards.

        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """
        with self.conn.cursor() as cur:
            cur.execute((SCRIPTS_DIR / "delete_normalized_concepts.sql").read_bytes())
        self.conn.commit()

    _drop_aliases_query = b"""
    DELETE FROM disease_aliases WHERE id IN (
        SELECT da.id FROM disease_aliases da LEFT JOIN disease_concepts dc
            ON dc.concept_id = da.concept_id
        WHERE dc.source = %s
    );
    """
    _drop_associations_query = b"""
    DELETE FROM disease_associations WHERE id IN (
        SELECT da.id FROM disease_associations da LEFT JOIN disease_concepts dc
            ON dc.concept_id = da.concept_id
        WHERE dc.source = %s
    );
    """
    _drop_labels_query = b"""
    DELETE FROM disease_labels WHERE id IN (
        SELECT ds.id FROM disease_labels ds LEFT JOIN disease_concepts dc
            ON dc.concept_id = ds.concept_id
        WHERE dc.source = %s
    );
    """
    _drop_xrefs_query = b"""
    DELETE FROM disease_xrefs WHERE id IN (
        SELECT dx.id FROM disease_xrefs dx LEFT JOIN disease_concepts dc
            ON dc.concept_id = dx.concept_id
        WHERE dc.source = %s
    );
    """
    _drop_concepts_query = b"DELETE FROM disease_concepts WHERE source = %s;"
    _drop_source_query = b"DELETE FROM disease_sources ds WHERE ds.name = %s;"

    def delete_source(self, src_name: SourceName) -> None:
        """Delete all data for a source. Use when updating source data.

        All of the foreign key relations make deletes *extremely* slow, so this method
        drops and then re-adds them once deletes are finished. This makes it a little
        brittle, and it'd be nice to revisit in the future to perform as a single
        atomic transaction.

        Refreshing the materialized view at the end might be redundant, because
        this method will almost always be called right before more data is written,
        but it's probably necessary just in case that doesn't happen.

        :param src_name: name of source to delete
        :raise DatabaseWriteException: if deletion call fails
        """
        with self.conn.cursor() as cur:
            cur.execute(self._drop_aliases_query, [src_name.value])
            cur.execute(self._drop_associations_query, [src_name.value])
            cur.execute(self._drop_labels_query, [src_name.value])
            cur.execute(self._drop_xrefs_query, [src_name.value])
        self._drop_fkeys()
        self._drop_indexes()

        with self.conn.cursor() as cur:
            cur.execute(self._drop_concepts_query, [src_name.value])
            cur.execute(self._drop_source_query, [src_name.value])
            self.conn.commit()

        self._add_fkeys()
        self._add_indexes()
        self._refresh_views()

    def complete_write_transaction(self) -> None:
        """Conclude transaction or batch writing if relevant."""
        if not self.conn.closed:
            try:
                self._refresh_views()
            except UndefinedTable:
                self.conn.rollback()

    def close_connection(self) -> None:
        """Perform any manual connection closure procedures if necessary."""
        if not self.conn.closed:
            self.conn.commit()
            self.conn.close()

    def load_from_remote(self, url: str | None) -> None:
        """Load DB from remote dump. Warning: Deletes all existing data. If not
        passed as an argument, will try to grab latest release from VICC S3 bucket.

        :param url: location of .tar.gz file created from output of pg_dump
        :raise DatabaseException: if unable to retrieve file from URL or if psql
            command fails
        """
        if not url:
            url = "https://vicc-normalizers.s3.us-east-2.amazonaws.com/disease_normalization/postgresql/disease_norm_latest.sql.tar.gz"
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = Path(tempdir)
            temp_tarfile = tempdir_path / "disease_norm_latest.tar.gz"
            with requests.get(url, stream=True, timeout=30) as r:
                try:
                    r.raise_for_status()
                except requests.HTTPError as e:
                    msg = f"Unable to retrieve PostgreSQL dump file from {url}"
                    raise DatabaseException(msg) from e
                with temp_tarfile.open("wb") as h:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            h.write(chunk)
            tar = tarfile.open(temp_tarfile, "r:gz")  # noqa: SIM115
            tar_dump_file = next(
                f for f in tar.getmembers() if f.name.startswith("disease_norm_")
            )
            tar.extractall(path=tempdir_path, members=[tar_dump_file])  # noqa: S202 RUF100
            dump_file = tempdir_path / tar_dump_file.name

            if self.conn.info.password:
                pw_param = f"-W {self.conn.info.password}"
            else:
                pw_param = "-w"

            self.drop_db()
            system_call = f"psql -d {self.conn.info.dbname} -U {self.conn.info.user} {pw_param} -f {dump_file.absolute()}"
            result = os.system(system_call)  # noqa: S605
        if result != 0:
            msg = f"System call '{result}' returned failing exit code."
            raise DatabaseException(msg)

    def export_db(self, output_directory: Path) -> None:
        """Dump DB to specified location.

        :param export_location: path to directory to save DB dump in
        :return: Nothing, but saves results of pg_dump to file named
            ``disease_norm_<date and time>.sql``
        :raise ValueError: if output directory isn't a directory or doesn't exist
        :raise DatabaseException: if psql call fails
        """
        if not output_directory.is_dir() or not output_directory.exists():
            msg = (
                f"Output location {output_directory} isn't a directory or doesn't exist"
            )
            raise ValueError(msg)
        now = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d%H%M%S")
        output_location = output_directory / f"disease_norm_{now}.sql"
        user = self.conn.info.user
        host = self.conn.info.host
        port = self.conn.info.port
        database_name = self.conn.info.dbname
        pw_param = f"-W {self.conn.info.password}" if self.conn.info.password else "-w"

        system_call = f"pg_dump -E UTF8 -f {output_location} -U {user} {pw_param} -h {host} -p {port} {database_name}"
        _logger.debug("Executing DB dump system call: %s", system_call)
        result = os.system(system_call)  # noqa: S605
        if result != 0:
            msg = f"System call '{system_call}' returned failing exit code."
            raise DatabaseException(msg)
