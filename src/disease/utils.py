"""idk."""

from disease.database import AbstractDatabase
from disease.schemas import RecordType, SourceName


def get_term_mappings(
    database: AbstractDatabase, scope: RecordType | SourceName
) -> list[dict]:
    """Tlisdlfkjo

    Columns
    * concept ID
    * name
    * aliases
    * xrefs
    """
    if isinstance(scope, SourceName):
        record_type = RecordType.IDENTITY
        src_name = scope
    else:
        record_type = RecordType.MERGER
        src_name = None

    results = []
    for record in database.get_all_records(record_type=record_type):
        if src_name and record["src_name"] != src_name:
            continue

        results.append(
            {
                "concept_id": record["concept_id"],
                "label": record["label"],
                "aliases": record.get("aliases", []),
                "xrefs": record.get("xrefs", []) + record.get("associated_with", []),
            }
        )
    return results
