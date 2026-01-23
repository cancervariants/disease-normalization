"""Provide miscellaneous utilities related to disease term normalization."""

import logging
from collections.abc import Generator

from disease.database import AbstractDatabase
from disease.schemas import RecordType, SourceMeta, SourceName


def get_source_meta(
    database: AbstractDatabase,
    scope: RecordType | SourceName,
) -> list[SourceMeta]:
    """Get source metadata (e.g. version info etc) for given sources

    Use in downstream applications such as datadumps.

    :param database: instance of DB connection to get records from
    :param scope: constrain record scope, either to a kind of record or to a specific source
    :return: list of source metadata descriptions
    :raise KeyError: if unrecognized source
    """

    def _lookup_meta(database: AbstractDatabase, source_name: SourceName) -> SourceMeta:
        meta = database.get_source_metadata(source_name)
        if not meta:
            msg = f"Unrecognized source: {source_name}"
            raise KeyError(msg)
        return meta

    if isinstance(scope, SourceName):
        return [_lookup_meta(database, scope)]
    return [_lookup_meta(database, source_name) for source_name in SourceName]


def get_term_mappings(
    database: AbstractDatabase,
    scope: RecordType | SourceName,
    cancer_only: bool = False,
) -> Generator[dict, None, None]:
    """Produce dict objects for known concepts (name + ID) plus other possible referents

    Use in downstream applications such as autocompletion.

    :param database: instance of DB connection to get records from
    :param scope: constrain record scope, either to a kind of record or to a specific source
    :param cancer_only: whether to just include cancer terms (not supported by all sources)
    :return: Generator yielding mapping objects
    """
    if isinstance(scope, SourceName):
        record_type = RecordType.IDENTITY
        src_name = scope
    else:
        record_type = scope
        src_name = None

    for record in database.get_all_records(record_type=record_type):
        if src_name and record["src_name"] != src_name:
            continue
        if cancer_only and record.get("oncologic_disease") is not True:
            continue

        yield {
            "concept_id": record["concept_id"],
            "label": record["label"],
            "aliases": record.get("aliases", []),
            "xrefs": record.get("xrefs", []) + record.get("associated_with", []),
        }


def initialize_logs(log_level: int = logging.INFO) -> None:
    """Configure logging.

    :param log_level: app log level to set
    """
    logging.basicConfig(
        filename=f"{__package__}.log",
        format="[%(asctime)s] - %(name)s - %(levelname)s : %(message)s",
    )
    logger = logging.getLogger(__package__)
    logger.setLevel(log_level)
