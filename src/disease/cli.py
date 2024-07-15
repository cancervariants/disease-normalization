"""Provides a CLI util to make updates to normalizer database."""

import logging
import os
from collections.abc import Collection
from pathlib import Path
from timeit import default_timer as timer

import click

from disease import SOURCES_FOR_MERGE, SOURCES_LOWER_LOOKUP
from disease.database.database import (
    AbstractDatabase,
    DatabaseException,
    DatabaseReadException,
    DatabaseWriteException,
    create_db,
)
from disease.schemas import SourceName

_logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure logging."""
    logging.basicConfig(
        filename=f"{__package__}.log",
        format="[%(asctime)s] - %(name)s - %(levelname)s : %(message)s",
    )
    logging.getLogger(__package__).setLevel(logging.DEBUG)


@click.command()
@click.option("--db_url", help="URL endpoint for the application database.")
@click.option("--verbose", "-v", is_flag=True, help="Print result to console if set.")
def check_db(db_url: str, verbose: bool = False) -> None:
    """Perform basic checks on DB health and population. Exits with status code 1
    if DB schema is uninitialized or if critical tables appear to be empty.

    \f
    :param db_url: URL to normalizer database
    :param verbose: if true, print result to console
    """  # noqa: D301
    _configure_logging()
    db = create_db(db_url, False)
    if not db.check_schema_initialized():
        if verbose:
            click.echo("Health check failed: DB schema uninitialized.")
        click.get_current_context().exit(1)

    if not db.check_tables_populated():
        if verbose:
            click.echo("Health check failed: DB is incompletely populated.")
        click.get_current_context().exit(1)

    msg = "DB health check successful: tables appear complete."
    if verbose:
        click.echo(msg)
    _logger.info(msg)


@click.command()
@click.option("--data_url", help="URL to data dump")
@click.option("--db_url", help="URL endpoint for the application database.")
def update_from_remote(data_url: str | None, db_url: str) -> None:
    """Update data from remotely-hosted DB dump. By default, fetches from latest
    available dump on VICC S3 bucket; specific URLs can be provided instead by
    command line option or DISEASE_NORM_REMOTE_DB_URL environment variable.

    \f
    :param data_url: user-specified location to pull DB dump from
    :param db_url: URL to normalizer database
    """  # noqa: D301
    _configure_logging()
    if not click.confirm("Are you sure you want to overwrite existing data?"):
        click.get_current_context().exit()
    if not data_url:
        data_url = os.environ.get("DISEASE_NORM_REMOTE_DB_URL")
    db = create_db(db_url, False)
    try:
        db.load_from_remote(data_url)
    except NotImplementedError:
        click.echo(
            "Error: Fetching remote data dump not supported for "
            f"{db.__class__.__name__}"
        )
        click.get_current_context().exit(1)
    except DatabaseException as e:
        click.echo(f"Encountered exception during update: {e!s}")
        click.get_current_context().exit(1)
    _logger.info("Successfully loaded data from remote snapshot.")


@click.command()
@click.option(
    "--output_directory",
    "-o",
    help="Output location to write to",
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--db_url", help="URL endpoint for the application database.")
def dump_database(output_directory: Path, db_url: str) -> None:
    """Dump data from database into file.

    \f
    :param output_directory: path to existing directory
    :param db_url: URL to normalizer database
    """  # noqa: D301
    _configure_logging()
    if not output_directory:
        output_directory = Path()

    db = create_db(db_url, False)
    try:
        db.export_db(output_directory)
    except NotImplementedError:
        click.echo(
            f"Error: Dumping data to file not supported for {db.__class__.__name__}"
        )
        click.get_current_context().exit(1)
    except DatabaseException as e:
        click.echo(f"Encountered exception during update: {e!s}")
        click.get_current_context().exit(1)
    _logger.info("Database dump successful.")


def _update_sources(
    sources: Collection[SourceName],
    db: AbstractDatabase,
    update_merged: bool,
    from_local: bool,
) -> None:
    """Update selected normalizer sources.

    :param sources: names of sources to update
    :param db: database instance
    :param update_merged: if true, retain processed records to use in updating merged
        records
    :param from_local: if true, use locally available data only
    """
    processed_ids = []
    for n in sources:
        delete_time = _delete_source(n, db)
        _load_source(n, db, delete_time, processed_ids, from_local)

    if update_merged:
        _load_merge(db, set(processed_ids))


def _delete_source(n: SourceName, db: AbstractDatabase) -> float:
    """Delete individual source data.

    :param n: name of source to delete
    :param db: database instance
    :return: time taken (in seconds) to delete
    """
    msg = f"Deleting {n.value}..."
    click.echo(f"\n{msg}")
    _logger.info(msg)
    start_delete = timer()
    db.delete_source(n)
    end_delete = timer()
    delete_time = end_delete - start_delete
    msg = f"Deleted {n.value} in {delete_time:.5f} seconds."
    click.echo(f"{msg}\n")
    _logger.info(msg)
    return delete_time


def _load_source(
    n: SourceName,
    db: AbstractDatabase,
    delete_time: float,
    processed_ids: list[str],
    from_local: bool,
) -> None:
    """Load individual source data.

    :param n: name of source
    :param db: database instance
    :param delete_time: time taken (in seconds) to run deletion
    :param processed_ids: in-progress list of processed disease IDs
    :param from_local: if true, use locally available data
    """
    msg = f"Loading {n.value}..."
    click.echo(msg)
    _logger.info(msg)
    start_load = timer()

    # used to get source class name from string
    try:
        from disease.etl import DO, OMIM, Mondo, NCIt, OncoTree  # noqa: F401
    except ModuleNotFoundError as e:
        click.echo(
            f"Encountered ModuleNotFoundError attempting to import {e.name}. Are ETL dependencies installed?"
        )
        click.get_current_context().exit()
    SourceClass = eval(n.value)  # noqa: N806 S307 PGH001

    source = SourceClass(database=db, silent=False)
    processed_ids += source.perform_etl(use_existing=from_local)
    end_load = timer()
    load_time = end_load - start_load
    msg = f"Loaded {n.value} in {load_time:.5f} seconds."
    click.echo(msg)
    _logger.info(msg)
    msg = f"Total time for {n.value}: {(delete_time + load_time):.5f} seconds."
    click.echo(msg)
    _logger.info(msg)


def _delete_normalized_data(database: AbstractDatabase) -> None:
    """Delete normalized concepts

    :param database: DB instance
    """
    click.echo("\nDeleting normalized records...")
    start_delete = timer()
    try:
        database.delete_normalized_concepts()
    except (DatabaseReadException, DatabaseWriteException) as e:
        click.echo(f"Encountered exception during normalized data deletion: {e}")
        click.get_current_context().exit(1)
    end_delete = timer()
    delete_time = end_delete - start_delete
    click.echo(f"Deleted normalized records in {delete_time:.5f} seconds.")


def _load_merge(db: AbstractDatabase, processed_ids: set[str]) -> None:
    """Load merged concepts

    :param db: database instance
    :param processed_ids: in-progress list of processed disease IDs
    """
    start = timer()
    _delete_normalized_data(db)
    if not processed_ids:
        processed_ids = set()
        for source in SOURCES_FOR_MERGE:
            processed_ids |= db.get_all_concept_ids(source)

    try:
        from disease.etl.merge import Merge
    except ModuleNotFoundError as e:
        click.echo(
            f"Encountered ModuleNotFoundError attempting to import {e.name}. Are ETL dependencies installed?"
        )
        click.get_current_context().exit()

    merge = Merge(database=db)
    click.echo("Constructing normalized records...")
    merge.create_merged_concepts(processed_ids)
    end = timer()
    click.echo(
        f"Merged concept generation completed in " f"{(end - start):.5f} seconds"
    )


@click.command()
@click.option("--sources", help="The source(s) you wish to update separated by spaces.")
@click.option("--aws_instance", is_flag=True, help="Using AWS DynamodDB instance.")
@click.option("--db_url", help="URL endpoint for the application database.")
@click.option("--update_all", is_flag=True, help="Update all normalizer sources.")
@click.option(
    "--update_merged",
    is_flag=True,
    help="Update concepts for normalize endpoint from accepted sources.",
)
@click.option(
    "--from_local",
    is_flag=True,
    default=False,
    help="Use most recent local source data instead of fetching latest versions.",
)
def update_db(
    sources: str,
    aws_instance: bool,
    db_url: str,
    update_all: bool,
    update_merged: bool,
    from_local: bool,
) -> None:
    """Update selected normalizer source(s) in the disease database.

    \f
    :param sources: names of sources to update, comma-separated
    :param aws_instance: if true, use cloud instance
    :param db_url: URI pointing to database
    :param update_all: if true, update all sources (ignore `normalizer` parameter)
    :param update_merged: if true, update normalized records
    :param from_local: if true, use locally available data only
    """  # noqa: D301
    _configure_logging()
    db = create_db(db_url, aws_instance)

    if update_all:
        _update_sources(list(SourceName), db, update_merged, from_local)
    elif not sources:
        if update_merged:
            _load_merge(db, set())
        else:
            ctx = click.get_current_context()
            click.echo(
                "Must either enter 1 or more sources, or use `--update_all` parameter"
            )
            click.echo(ctx.get_help())
            ctx.exit()
    else:
        sources_split = sources.lower().split()

        if len(sources_split) == 0:
            msg = "Must enter one or more source names"
            raise Exception(msg)

        non_sources = set(sources_split) - set(SOURCES_LOWER_LOOKUP)

        if len(non_sources) != 0:
            msg = f"Not valid source(s): {non_sources}"
            raise Exception(msg)

        sources_to_update = {SourceName(SOURCES_LOWER_LOOKUP[s]) for s in sources_split}
        _update_sources(sources_to_update, db, update_merged, from_local)
    _logger.info("Database update successful.")


if __name__ == "__main__":
    update_db()
