"""Provide miscellaneous utilities related to disease term normalization."""

from collections.abc import Generator

from disease.database import AbstractDatabase
from disease.schemas import RecordType, SourceName


def get_term_mappings(
    database: AbstractDatabase, scope: RecordType | SourceName
) -> Generator[dict, None, None]:
    """Produce dict objects for known concepts (name + ID) plus other possible referents

    Use in downstream applications such as autocompletion.

    :param database: instance of DB connection to get records from
    :param scope: constrain record scope, either to a kind of record or to a specific source
    :return: Generator yielding mapping objects
    """
    if isinstance(scope, SourceName):
        record_type = RecordType.IDENTITY
        src_name = scope
    else:
        record_type = RecordType.MERGER
        src_name = None

    for record in database.get_all_records(record_type=record_type):
        if src_name and record["src_name"] != src_name:
            continue

        yield {
            "concept_id": record["concept_id"],
            "label": record["label"],
            "aliases": record.get("aliases", []),
            "xrefs": record.get("xrefs", []) + record.get("associated_with", []),
        }
