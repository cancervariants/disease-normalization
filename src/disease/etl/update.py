"""Provide functions to perform Disease Normalizer updates."""

import logging
from timeit import default_timer as timer

import click

from disease.database.database import (
    AbstractDatabase,
    DatabaseReadException,
    DatabaseWriteException,
)
from disease.schemas import SourceName

_logger = logging.getLogger(__name__)


def _emit_info_msg(msg: str, silent: bool) -> None:
    """Handle info message display.

    :param msg: message to log/print
    :param silent: if True, don't print to console
    """
    if not silent:
        click.echo(msg)
    _logger.info(msg)


def delete_source(
    source: SourceName, db: AbstractDatabase, silent: bool = True
) -> float:
    """Delete all data for an individual source.

    :param source: name of source to delete data for
    :param db: database instance
    :param silent: if True, suppress console output
    :return: time spent deleting source
    """
    _emit_info_msg(f"Deleting {source.value}...", silent)
    start_delete = timer()
    db.delete_source(source)
    end_delete = timer()
    delete_time = end_delete - start_delete
    _emit_info_msg(f"Deleted {source.value} in {delete_time:.5f} seconds.", silent)
    return delete_time


_etl_dependency_help = "Are ETL dependencies installed? See the Installation page in the documentation for more info."


def load_source(
    source: SourceName, db: AbstractDatabase, use_existing: bool, silent: bool = True
) -> tuple[float, set[str]]:
    """Load data for an individual source.

    :param source: name of source to load data for
    :param db: database instance
    :param use_existing: if True, use latest available version of local data
    :param silent: if True, suppress console output
    :return: time spent loading data, and set of processed IDs from that source
    """
    _emit_info_msg(f"Loading {source.value}...", silent)
    start_load = timer()

    # used to get source class name from string
    try:
        from disease.etl import (  # noqa: PLC0415
            DO,
            OMIM,
            DiseaseNormalizerEtlError,
            Mondo,
            NCIt,
            OncoTree,
        )
    except ModuleNotFoundError as e:
        click.echo(
            f"Encountered ModuleNotFoundError attempting to import {e.name}. {_etl_dependency_help}"
        )
        click.get_current_context().exit()
    sources_table = {
        SourceName.DO: DO,
        SourceName.MONDO: Mondo,
        SourceName.NCIT: NCIt,
        SourceName.OMIM: OMIM,
        SourceName.ONCOTREE: OncoTree,
    }

    source_class = sources_table[source](database=db, silent=silent)
    try:
        processed_ids = source_class.perform_etl(use_existing)
    except DiseaseNormalizerEtlError as e:
        msg = f"Encountered error while loading {source}: {e}."
        _logger.exception(msg)
        if not silent:
            click.echo(msg)
        click.get_current_context().exit(1)
    end_load = timer()
    load_time = end_load - start_load
    _emit_info_msg(
        f"Loaded {len(processed_ids)} records from {source.value} in {load_time:.5f} seconds.",
        silent,
    )

    # don't forward any concept IDs that we don't want to use for group generation
    if not source_class.store_ids:
        processed_ids = []

    return (load_time, set(processed_ids))


def update_source(
    source: SourceName, db: AbstractDatabase, use_existing: bool, silent: bool = True
) -> set[str]:
    """Refresh data for an individual disease data source.

    For example, to completely refresh Mondo data:

    >>> from disease.schemas import SourceName
    >>> from disease.database import create_db
    >>> from disease.etl.update import update_source
    >>> db = create_db()
    >>> processed_ids = update_source(SourceName.MONDO, db)

    :param source: name of source to update
    :param db: database instance
    :param use_existing: if True, use latest available local data
    :param silent: if True, suppress console output
    :return: IDs for records created from source
    """
    delete_time = delete_source(source, db, silent)
    load_time, processed_ids = load_source(source, db, use_existing, silent)
    _emit_info_msg(
        f"Total time for {source.value}: {(delete_time + load_time):.5f} seconds.",
        silent,
    )
    return processed_ids


def update_all_sources(
    db: AbstractDatabase, use_existing: bool, silent: bool = True
) -> set[str]:
    """Refresh data for all disease record sources.

    :param db: database instance
    :param use_existing: if True, use latest available local data for all sources
    :param silent: if True, suppress console output
    :return: IDs processed from all sources
    """
    processed_ids: list[str] = []
    for source in SourceName:
        source_ids = update_source(source, db, use_existing, silent)
        processed_ids += list(source_ids)
    return set(processed_ids)


def delete_normalized(database: AbstractDatabase, silent: bool = True) -> None:
    """Delete normalized concepts.

    :param database: DB instance
    :param silent: if True, suppress console output
    """
    _emit_info_msg("\nDeleting normalized records...", silent)
    start_delete = timer()
    try:
        database.delete_normalized_concepts()
    except (DatabaseReadException, DatabaseWriteException):
        msg = "Encountered exception during normalized data deletion"
        _logger.exception(msg)
        click.echo(msg)
        raise
    end_delete = timer()
    delete_time = end_delete - start_delete
    _emit_info_msg(f"Deleted normalized records in {delete_time:.5f} seconds.", silent)


def update_normalized(
    db: AbstractDatabase, processed_ids: set[str] | None, silent: bool = True
) -> None:
    """Delete existing and update merged normalized records.

    :param db: database instance
    :param processed_ids: IDs to form normalized records from. Provide if available to
        cut down on some potentially slow database calls. If unavailable, this method
        will fetch all known IDs directly.
    :param silent: if True, suppress console output
    """
    start = timer()
    delete_normalized(db, silent)
    if not processed_ids:
        processed_ids = db.get_all_concept_ids()

    try:
        from disease.etl.merge import Merge  # noqa: PLC0415
    except ModuleNotFoundError as e:
        msg = f"Encountered ModuleNotFoundError attempting to import {e.name}. {_etl_dependency_help}"
        if not silent:
            click.echo(msg)
        _logger.exception(msg)
        click.get_current_context().exit()

    merge = Merge(database=db)
    if not silent:
        click.echo("Constructing normalized records...")
    merge.create_merged_concepts(processed_ids)
    end = timer()
    _emit_info_msg(
        f"Merged concept generation completed in {(end - start):.5f} seconds",
        silent,
    )


def update_all_and_normalize(
    db: AbstractDatabase, use_existing: bool, silent: bool = True
) -> None:
    """Update all sources as well as normalized records.

    For example, to completely refresh all Disease Normalizer data:

    >>> from disease.database import create_db
    >>> from disease.etl.update import update_all_and_normalize
    >>> db = create_db()
    >>> update_all_and_normalize(db, False)

    :param db: database instance
    :param use_existing: if True, use latest local copy of data
    :param silent: if True, suppress console output
    """
    processed_ids = update_all_sources(db, use_existing, silent)
    update_normalized(db, processed_ids, silent)
