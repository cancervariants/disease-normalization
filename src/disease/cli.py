"""Provides a CLI util to make updates to normalizer database."""

import logging
import os
from pathlib import Path

import click

from disease import __version__
from disease.config import config
from disease.database.database import DatabaseException, create_db
from disease.etl.update import update_all_sources, update_normalized, update_source
from disease.logs import initialize_logs
from disease.schemas import SourceName

_logger = logging.getLogger(__name__)


URL_DESCRIPTION = 'URL endpoint for the application database. Can either be a URL to a local DynamoDB server (e.g. "http://localhost:8001") or a libpq-compliant PostgreSQL connection description (e.g. "postgresql://postgres:password@localhost:5432/gene_normalizer").'
SILENT_MODE_DESCRIPTION = "Suppress output to console."


def _initialize_app() -> None:
    if config.debug:
        initialize_logs(logging.DEBUG)
    else:
        initialize_logs()


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Manage Disease Normalizer data."""


@cli.command()
@click.option("--db_url", help=URL_DESCRIPTION)
@click.option("--silent", is_flag=True, default=False, help=SILENT_MODE_DESCRIPTION)
def check_db(db_url: str, silent: bool) -> None:
    """Perform basic checks on DB health and population. Exits with status code 1
    if DB schema is uninitialized or if critical tables appear to be empty.

        $ disease-normalizer check-db
        $ echo $?
        1  # indicates failure

    This command is equivalent to the combination of the database classes'
    ``check_schema_initialized()`` and ``check_tables_populated()`` methods:

    >>> from disease.database import create_db
    >>> db = create_db()
    >>> db.check_schema_initialized() and db.check_tables_populated()
    True  # DB passes checks

    \f
    :param db_url: URL to normalizer database
    :param silent: if true, suppress console output
    """  # noqa: D301
    _initialize_app()
    db = create_db(db_url, False)
    if not db.check_schema_initialized():
        if not silent:
            click.echo("Health check failed: DB schema uninitialized.")
        click.get_current_context().exit(1)

    if not db.check_tables_populated():
        if not silent:
            click.echo("Health check failed: DB is incompletely populated.")
        click.get_current_context().exit(1)

    msg = "DB health check successful: tables appear complete."
    if not silent:
        click.echo(msg)
    _logger.info(msg)


@cli.command()
@click.option("--data_url", help="URL to data dump")
@click.option("--db_url", help=URL_DESCRIPTION)
@click.option("--silent", is_flag=True, default=False, help=SILENT_MODE_DESCRIPTION)
def update_from_remote(data_url: str | None, db_url: str, silent: bool) -> None:
    """Update data from remotely-hosted DB dump. By default, fetches from latest
    available dump on VICC S3 bucket; specific URLs can be provided instead by
    command line option or DISEASE_NORM_REMOTE_DB_URL environment variable.

    \f
    :param data_url: user-specified location to pull DB dump from
    :param db_url: URL to normalizer database
    :param silent: if true, suppress console output
    """  # noqa: D301
    _initialize_app()
    if not click.confirm("Are you sure you want to overwrite existing data?"):
        click.get_current_context().exit()
    if not data_url:
        data_url = os.environ.get("DISEASE_NORM_REMOTE_DB_URL")
    db = create_db(db_url, False)
    try:
        db.load_from_remote(data_url)
    except NotImplementedError:
        if not silent:
            click.echo(
                f"Error: Fetching remote data dump not supported for {db.__class__.__name__}"
            )
        click.get_current_context().exit(1)
    except DatabaseException as e:
        if not silent:
            click.echo(f"Encountered exception during update: {e!s}")
        _logger.exception(
            "Encountered exception. `data_url`=%s, `db_url`=%s", data_url, db_url
        )
        click.get_current_context().exit(1)
    _logger.info("Successfully loaded data from remote snapshot.")


@cli.command()
@click.option(
    "--output_directory",
    "-o",
    help="Output location to write to",
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--db_url", help=URL_DESCRIPTION)
@click.option("--silent", is_flag=True, default=False, help=SILENT_MODE_DESCRIPTION)
def dump_database(output_directory: Path, db_url: str, silent: bool) -> None:
    """Dump data from database into file.

    \f
    :param output_directory: path to existing directory
    :param db_url: URL to normalizer database
    :param silent: if True, suppress output to console
    """  # noqa: D301
    _initialize_app()
    if not output_directory:
        output_directory = Path()

    db = create_db(db_url, False)
    try:
        db.export_db(output_directory)
    except NotImplementedError:
        msg = f"Error: Dumping data to file not supported for {db.__class__.__name__}"
        if not silent:
            click.echo(msg)
        _logger.exception(msg)
        click.get_current_context().exit(1)
    except DatabaseException as e:
        if not silent:
            click.echo(f"Encountered exception during update: {e!s}")
        _logger.exception(
            "Encountered exception. `data_url`=%s, `db_url`=%s",
            output_directory,
            db_url,
        )
        click.get_current_context().exit(1)
    _logger.info("Database dump successful.")


@cli.command()
@click.argument("sources", nargs=-1)
@click.option("--all", "all_", is_flag=True, help="Update records for all sources.")
@click.option("--normalize", is_flag=True, help="Create normalized records.")
@click.option("--db_url", help=URL_DESCRIPTION)
@click.option("--aws_instance", is_flag=True, help="Use cloud DynamodDB instance.")
@click.option(
    "--use_existing",
    is_flag=True,
    default=False,
    help="Use most recent locally-available source data instead of fetching latest version",
)
@click.option("--silent", is_flag=True, default=False, help=SILENT_MODE_DESCRIPTION)
def update(
    sources: tuple[str, ...],
    aws_instance: bool,
    db_url: str,
    all_: bool,
    normalize: bool,
    use_existing: bool,
    silent: bool,
) -> None:
    """Update provided normalizer SOURCES in the gene database.

    Valid SOURCES are "DO", "MONDO", "NCIt", "OMIM", and "OncoTree" (case is irrelevant).

    SOURCES are optional, but if not provided, either --all or --normalize must be used.

    For example, the following command will update DO and MONDO source records:

        $ disease-normalizer update DO MONDO

    To completely reload all source records and construct normalized concepts, use the
    --all and --normalize options:

        $ disease-normalizer update --all --normalize

    The Disease Normalizer will fetch the latest available data from all sources if local
    data is out-of-date. To suppress this and force usage of local files only, use the
    --use_existing flag:

        $ disease-normalizer update --all --use_existing

    \f
    :param sources: tuple of raw names of sources to update
    :param aws_instance: if true, use cloud instance
    :param db_url: URI pointing to database
    :param all_: if True, update all sources (ignore ``sources``)
    :param normalize: if True, update normalized records
    :param use_existing: if True, use most recent local data instead of fetching latest version
    :param silent: if True, suppress console output
    """  # noqa: D301
    _initialize_app()
    if len(sources) == 0 and (not all_) and (not normalize):
        click.echo(
            "Error: must provide SOURCES or at least one of --all, --normalize\n"
        )
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit(1)

    db = create_db(db_url, aws_instance)

    processed_ids = None
    if all_:
        processed_ids = update_all_sources(db, use_existing, silent=silent)
    elif sources:
        parsed_sources = set()
        failed_source_names = []
        for source in sources:
            try:
                parsed_sources.add(SourceName[source.upper()])
            except KeyError:
                failed_source_names.append(source)
        if len(failed_source_names) != 0:
            click.echo(f"Error: unrecognized sources: {failed_source_names}")
            click.echo(f"Valid source options are {list(SourceName)}")
            click.get_current_context().exit(1)

        working_processed_ids = set()
        for source_name in parsed_sources:
            working_processed_ids |= update_source(
                source_name, db, use_existing=use_existing, silent=silent
            )
        if len(sources) == len(SourceName):
            processed_ids = working_processed_ids

    if normalize:
        update_normalized(db, processed_ids, silent=silent)


if __name__ == "__main__":
    cli()
