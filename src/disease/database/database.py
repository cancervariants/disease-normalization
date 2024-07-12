"""Provide core database classes and helper methods.

Users shouldn't need to interact with the base class directly, but
:py:meth:`~disease.database.database.create_db` is the recommended way to create a
database connection.
"""

import abc
import sys
from collections.abc import Generator
from enum import Enum
from os import environ
from pathlib import Path
from typing import Any

import click

from disease.schemas import RecordType, RefType, SourceMeta, SourceName


class DatabaseException(Exception):  # noqa: N818
    """Create custom class for handling database exceptions"""


class DatabaseInitializationException(DatabaseException):
    """Create custom exception for errors during DB connection initialization."""


class DatabaseReadException(DatabaseException):
    """Create custom exception for lookup/read errors"""


class DatabaseWriteException(DatabaseException):
    """Create custom exception for write errors"""


class AbstractDatabase(abc.ABC):
    """Define a database interface."""

    @abc.abstractmethod
    def __init__(self, db_url: str | None = None, **db_args) -> None:
        """Initialize database instance.

        Generally, implementing classes should be able to construct a connection by
        something like a libpq URL. Any additional arguments or DB-specific parameters
        can be passed as keywords.

        :param db_url: address/connection description for database
        :param db_args: any DB implementation-specific parameters
        :raise DatabaseInitializationException: if initial setup fails
        """

    @abc.abstractmethod
    def list_tables(self) -> list[str]:
        """Return names of tables in database.

        :return: Table names in database
        """

    @staticmethod
    def _check_delete_okay() -> bool:
        """Check that environmental conditions permit DB deletion, and require
        confirmation.

        :raise DatabaseWriteException: if skip confirmation variable is set -- manual
        approval is required.
        """
        if environ.get(AWS_ENV_VAR_NAME, "") == AwsEnvName.PRODUCTION:
            if environ.get(SKIP_AWS_DB_ENV_NAME, "") == "true":
                msg = f"Must unset {SKIP_AWS_DB_ENV_NAME} env variable to enable drop_db()"
                raise DatabaseWriteException(msg)
            return click.confirm("Are you sure you want to delete existing data?")
        return True

    @abc.abstractmethod
    def drop_db(self) -> None:
        """Initiate total teardown of DB. Useful for quickly resetting the entirety of
        the data. Requires manual confirmation.

        :raise DatabaseWriteException: if called in a protected setting with
            confirmation silenced.
        """

    @abc.abstractmethod
    def check_schema_initialized(self) -> bool:
        """Check if database schema is properly initialized.

        :return: True if DB appears to be fully initialized, False otherwise
        """

    @abc.abstractmethod
    def check_tables_populated(self) -> bool:
        """Perform rudimentary checks to see if tables are populated.
        Emphasis is on rudimentary -- if some fiendish element has deleted half of the
        disease aliases, this method won't pick it up. It just wants to see if a few
        critical tables have at least a small number of records.

        :return: True if queries successful, false if DB appears empty
        """

    @abc.abstractmethod
    def initialize_db(self) -> None:
        """Perform all necessary parts of database setup. Should be tolerant of
        existing content -- ie, this method is also responsible for checking whether
        the DB is already set up.

        :raise DatabaseInitializationException: if initialization fails
        """

    @abc.abstractmethod
    def get_source_metadata(self, src_name: str | SourceName) -> SourceMeta | None:
        """Get license, versioning, data lookup, etc information for a source.

        :param src_name: name of the source to get data for
        :return: source metadata, if lookup is successful
        """

    @abc.abstractmethod
    def get_record_by_id(
        self, concept_id: str, case_sensitive: bool = True, merge: bool = False
    ) -> dict | None:
        """Fetch record corresponding to provided concept ID

        :param concept_id: concept ID for record
        :param case_sensitive: if true, performs exact lookup, which may be quicker.
            Otherwise, performs filter operation, which doesn't require correct casing.
        :param merge: if true, look for merged record; look for identity
            record otherwise.
        :return: complete record, if match is found; None otherwise
        """

    @abc.abstractmethod
    def get_refs_by_type(self, search_term: str, ref_type: RefType) -> list[str]:
        """Retrieve concept IDs for records matching the user's query. Other methods
        are responsible for actually retrieving full records.

        :param search_term: string to match against
        :param ref_type: type of match to look for.
        :return: list of associated concept IDs. Empty if lookup fails.
        """

    @abc.abstractmethod
    def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]:
        """Retrieve all available concept IDs for use in generating normalized records.

        :param source: optionally, just get all IDs for a specific source
        :return: Set of concept IDs as strings.
        """

    @abc.abstractmethod
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

        :param record_type: type of result to return
        :return: Generator that lazily provides records as they are retrieved
        """

    @abc.abstractmethod
    def add_source_metadata(self, src_name: SourceName, meta: SourceMeta) -> None:
        """Add new source metadata entry.

        :param src_name: name of source
        :param meta: known source attributes
        :raise DatabaseWriteException: if write fails
        """

    @abc.abstractmethod
    def add_record(self, record: dict, src_name: SourceName) -> None:
        """Add new record to database.

        :param record: record to upload
        :param src_name: name of source for record.
        """

    @abc.abstractmethod
    def add_merged_record(self, record: dict) -> None:
        """Add merged record to database.

        :param record: merged record to add
        """

    @abc.abstractmethod
    def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
        """Update the merged record reference of an individual record to a new value.

        :param concept_id: record to update
        :param merge_ref: new ref value
        :raise DatabaseWriteException: if attempting to update non-existent record
        """

    @abc.abstractmethod
    def delete_normalized_concepts(self) -> None:
        """Remove merged records from the database. Use when performing a new update
        of normalized data.

        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """

    @abc.abstractmethod
    def delete_source(self, src_name: SourceName) -> None:
        """Delete all data for a source. Use when updating source data.

        :param src_name: name of source to delete
        :raise DatabaseReadException: if DB client requires separate read calls and
            encounters a failure in the process
        :raise DatabaseWriteException: if deletion call fails
        """

    @abc.abstractmethod
    def complete_write_transaction(self) -> None:
        """Conclude transaction or batch writing if relevant."""

    @abc.abstractmethod
    def close_connection(self) -> None:
        """Perform any manual connection closure procedures if necessary."""

    @abc.abstractmethod
    def load_from_remote(self, url: str | None = None) -> None:
        """Load DB from remote dump. Warning: Deletes all existing data.

        :param url: remote location to retrieve gzipped dump file from
        :raise: NotImplementedError if not supported by DB
        """

    @abc.abstractmethod
    def export_db(self, export_location: Path) -> None:
        """Dump DB to specified location.

        :param export_location: path to save DB dump at
        :raise: NotImplementedError if not supported by DB
        """


# can be set to either `Dev`, `Staging`, or `Prod`
# ONLY set when wanting to access aws instance
AWS_ENV_VAR_NAME = "DISEASE_NORM_ENV"

# Set to "true" if want to skip db confirmation check. Should ONLY be used for
# deployment needs
SKIP_AWS_DB_ENV_NAME = "SKIP_AWS_CONFIRMATION"


class AwsEnvName(str, Enum):
    """AWS environment name that is being used"""

    DEVELOPMENT = "Dev"
    STAGING = "Staging"
    PRODUCTION = "Prod"


VALID_AWS_ENV_NAMES = {v.value for v in AwsEnvName.__members__.values()}


def confirm_aws_db_use(env_name: str) -> None:
    """Check to ensure that AWS instance should actually be used."""
    if click.confirm(
        f"Are you sure you want to use the AWS {env_name} database?", default=False
    ):
        click.echo(f"***DISEASE AWS {env_name.upper()} DATABASE IN USE***")
    else:
        click.echo("Exiting.")
        sys.exit()


def create_db(
    db_url: str | None = None, aws_instance: bool = False
) -> AbstractDatabase:
    """Database factory method. Checks environment variables and provided parameters
    and creates a DB instance.

    Generally prefers to return a DynamoDB instance, unless all DDB-relevant
    environment variables are unset and a libpq-compliant URI is passed to
    ``db_url``.

    :param db_url: address to database instance
    :param aws_instance: use hosted DynamoDB instance, not local DB
    :return: constructed Database instance
    """
    aws_env_var_set = AWS_ENV_VAR_NAME in environ
    if aws_env_var_set or aws_instance:
        from disease.database.dynamodb import DynamoDbDatabase

        db = DynamoDbDatabase()
    else:
        if db_url:
            endpoint_url = db_url
        elif "DISEASE_NORM_DB_URL" in environ:
            endpoint_url = environ["DISEASE_NORM_DB_URL"]
        else:
            endpoint_url = "http://localhost:8000"

        # prefer DynamoDB unless connection explicitly reads like a libpq URI
        if endpoint_url.startswith("postgres"):
            from disease.database.postgresql import PostgresDatabase

            db = PostgresDatabase(endpoint_url)
        else:
            from disease.database.dynamodb import DynamoDbDatabase

            db = DynamoDbDatabase(endpoint_url)
    return db
