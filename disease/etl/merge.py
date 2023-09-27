"""Create concept groups and merged records."""
from timeit import default_timer as timer
from typing import Collection, Dict, List, Set, Tuple

from disease import logger
from disease.database.database import AbstractDatabase
from disease.schemas import SourcePriority


class Merge:
    """Handles record merging."""

    def __init__(self, database: AbstractDatabase) -> None:
        """Initialize Merge instance.

        :param Database database: db instance to use for record retrieval and creation.
        """
        self._database = database
        self._groups = []  # list of tuples: (mondo_concept_id, set_of_ids)

    def create_merged_concepts(self, record_ids: Collection[str]) -> None:
        """Create concept groups, generate merged concept records, and update database.
        Our normalization protocols only generate record ID sets that include Mondo
        terms, meaning only Mondo IDs should be submitted to this method.

        :param record_ids: concept identifiers from which groups should be generated.
        """
        # build groups
        logger.info(f"Generating record ID sets from {len(record_ids)} records")
        start = timer()
        for concept_id in record_ids:
            try:
                record = self._database.get_record_by_id(concept_id)
            except AttributeError:
                logger.error(
                    f"`create_merged_concepts` received invalid "
                    f"concept ID: {concept_id}"
                )
                continue
            if not record:
                logger.error(f"generate_merged_concepts couldn't find " f"{concept_id}")
                continue
            xrefs = record.get("xrefs", None)
            if xrefs:
                group = set(xrefs + [concept_id])
            else:
                group = {concept_id}
            self._groups.append((concept_id, group))
        end = timer()
        self._database.complete_write_transaction()
        logger.debug(f"Built record ID sets in {end - start} seconds")

        # build merged concepts
        logger.info("Creating merged records and updating database...")
        start = timer()
        for record_id, group in self._groups:
            try:
                merged_record, merged_ids = self._generate_merged_record(group)
            except AttributeError:
                logger.error(
                    "`create_merged_concepts` received invalid group:"
                    f"{group} for concept {record_id}"
                )
                continue
            self._database.add_merged_record(merged_record)
            merge_ref = merged_record["concept_id"]

            for concept_id in merged_ids:
                self._database.update_merge_ref(concept_id, merge_ref)
        self._database.complete_write_transaction()
        end = timer()
        logger.info("merged concept generation successful.")
        logger.debug(f"Generated and added concepts in {end - start} seconds)")

    def _generate_merged_record(self, record_id_set: Set[str]) -> Tuple[Dict, List]:
        """Generate merged record from provided concept ID group.
        Where attributes are sets, they should be merged, and where they are
        scalars, assign from the highest-priority source where that attribute
        is non-null.

        Priority is NCIt > Mondo > OMIM > OncoTree> DO.

        :param Set record_id_set: group of concept IDs
        :return: completed merged drug object to be stored in DB, as well as
            a list of the IDs ultimately included in said record
        """
        records = []
        final_ids = []
        for record_id in record_id_set:
            record = self._database.get_record_by_id(record_id)
            if record:
                records.append(record)
                final_ids.append(record["concept_id"])
            else:
                logger.error(
                    f"generate_merged_record could not retrieve "
                    f"record for {record_id} in {record_id_set}"
                )

        def record_order(record: Dict) -> Tuple:
            """Provide priority values of concepts for sort function."""
            src = record["src_name"].upper()
            source_rank = SourcePriority[src].value
            return source_rank, record["concept_id"]

        records.sort(key=record_order)

        merged_properties = {
            "concept_id": records[0]["concept_id"],
            "aliases": set(),
            "associated_with": set(),
        }
        if len(records) > 1:
            merged_properties["xrefs"] = list({r["concept_id"] for r in records[1:]})

        set_fields = ["aliases", "associated_with"]
        scalar_fields = ["label", "pediatric_disease"]
        for record in records:
            for field in set_fields:
                if field in record:
                    merged_properties[field] |= set(record[field])
            for field in scalar_fields:
                if field not in merged_properties and field in record:
                    merged_properties[field] = record[field]

        for field in set_fields:
            field_value = merged_properties[field]
            if field_value:
                merged_properties[field] = list(field_value)
            else:
                del merged_properties[field]

        return merged_properties, final_ids
