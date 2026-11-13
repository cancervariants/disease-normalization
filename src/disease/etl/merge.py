"""Create concept groups and merged records."""

import logging
from collections.abc import Collection
from timeit import default_timer as timer

from ga4gh.core.models import ConceptMapping, Relation
from ga4gh.va_spec.base import Condition
from tqdm import tqdm

from disease.database.database import AbstractDatabase
from disease.schemas import (
    DISEASE_CONCEPT_TYPE,
    PREFIX_LOOKUP,
    Disease,
    NamespacePrefix,
    SourcePriority,
    coding_to_concept_id,
    concept_id_to_coding,
    disease_to_mapcon,
)

_logger = logging.getLogger(__name__)


class Merge:
    """Manage construction of record mergers for normalization."""

    def __init__(self, database: AbstractDatabase, silent: bool = True) -> None:
        """Initialize Merge instance.

        :param Database database: db instance to use for record retrieval and creation.
        :param silent: if ``True``, suppress console output
        """
        self._database = database
        self._silent = silent

    def create_merged_concepts(self, record_ids: Collection[str]) -> None:
        """Create concept groups, generate merged concept records, and update database.

        Our normalization protocols only generate record ID sets that include Mondo
        terms, meaning only Mondo IDs should be submitted to this method.

        Rather than a DFS of all record xrefs as with the other normalizers, here we just
        work from the xrefs provided by the Mondo record.

        :param record_ids: concept identifiers from which groups should be generated.
        """
        # build groups
        _logger.info("Generating record ID sets from %s records", len(record_ids))
        start = timer()
        groups = self._get_merged_concept_groups(record_ids)
        end = timer()
        self._database.complete_write_transaction()
        _logger.debug("Built record ID sets in %s seconds", end - start)

        # build merged concepts
        _logger.info("Creating merged records and updating database...")
        start = timer()
        for record_id, group in tqdm(groups, ncols=80, disable=self._silent):
            try:
                merged_record, merged_ids = self._generate_merged_record(group)
            except AttributeError:
                _logger.exception(
                    "`create_merged_concepts` received invalid group: %s for concept %s",
                    group,
                    record_id,
                )
                continue
            self._database.add_merged_record(merged_record)

            merge_ref = merged_record.id
            for concept_id in merged_ids:
                self._database.update_merge_ref(concept_id, merge_ref)
        self._database.complete_write_transaction()
        end = timer()
        _logger.info("merged concept generation successful.")
        _logger.debug("Generated and added concepts in %s seconds", end - start)

    def _get_merged_concept_groups(
        self, record_ids: Collection[str]
    ) -> list[tuple[str, set[str]]]:
        """Generate normalized groups

        :param record_ids: IDs to form groups from
        :return: tuples of (mondo_id, {set of IDs contained within})
        :raise ValueError: if submitted IDs aren't from Mondo
        """
        groups = []
        for concept_id in tqdm(record_ids, ncols=80, disable=self._silent):
            if not concept_id.startswith(NamespacePrefix.MONDO.value):
                msg = f"Only Mondo IDs should be used as the basis for normalized groups; received {concept_id} instead"
                raise ValueError(msg)
            try:
                # temporary -- remove once full domain model migration is complete
                _record = self._database.get_record_by_id(concept_id)
                if not _record:
                    _logger.error(
                        "generate_merged_concepts couldn't find %s", concept_id
                    )
                    continue
                record = disease_to_mapcon(Disease(**_record))
            except AttributeError:
                _logger.exception(
                    "`create_merged_concepts` received invalid concept ID: %s",
                    concept_id,
                )
                continue
            xrefs = (
                {
                    coding_to_concept_id(m.coding)
                    for m in record.mappings
                    if m.relation == Relation.EXACT_MATCH
                }
                if record.mappings
                else set()
            )
            group = {*xrefs, concept_id} if xrefs else {concept_id}
            groups.append((concept_id, group))
        return groups

    def _generate_merged_record(
        self, record_id_set: set[str]
    ) -> tuple[Condition, list]:
        """Generate merged record from provided concept ID group.

        Misc notes
        * Where attributes are sets, they should be merged, and where they are
        scalars, assign from the highest-priority source where that attribute
        is non-null. Value priority is NCIt > Mondo > OMIM > OncoTree> DO.
        * The exception is with xrefs, which (for all groups of n > 1) is constructed by
        taking the `record_id_set` value, dropping all records which (for whatever reason)
        weren't able to be found in the DB, and dropping the ID that will be used as the
        primary coding for the record

        :param record_id_set: group of concept IDs
        :return: completed merged drug object to be stored in DB, as well as
            a list of the IDs ultimately included in said record
        """
        records: list[Condition] = []
        final_ids = []
        for record_id in record_id_set:
            _record = self._database.get_record_by_id(record_id)
            if _record:
                disease = disease_to_mapcon(Disease(**_record))
                records.append(disease)
                final_ids.append(disease.id)
            else:
                _logger.error(
                    "generate_merged_record could not retrieve record for %s in %s",
                    record_id,
                    record_id_set,
                )

        def record_order(disease: Condition) -> tuple:
            """Provide priority values of concepts for sort function."""
            prefix = disease.id.split(":", 1)[0]
            src_name = PREFIX_LOOKUP[prefix.lower()]
            source_rank = SourcePriority[src_name.upper()].value
            return source_rank, disease.id

        records.sort(key=record_order)

        concept_id = records[0].id
        name = records[0].name
        aliases = records[0].aliases or []
        mappings = records[0].mappings or []
        extensions = records[0].extensions or []

        for record in records[1:]:
            if record.aliases:
                aliases.extend(record.aliases)
            if record.mappings:
                mappings.extend(
                    [
                        *record.mappings,
                        ConceptMapping(
                            coding=record.primaryCoding, relation=Relation.EXACT_MATCH
                        ),
                    ]
                )
            if record.extensions:
                extensions.extend(record.extensions)

        primary_coding = concept_id_to_coding(concept_id)

        aliases = list(set(aliases)) if aliases else None
        mappings = (
            list(
                {
                    m.coding.id: m for m in mappings if m.coding.id != primary_coding.id
                }.values()
            )
            if mappings
            else None
        )
        extensions = (
            list({e.name: e for e in extensions}.values()) if extensions else None
        )

        merged_disease = Condition(
            id=f"normalize.disease.{concept_id}",
            conceptType=DISEASE_CONCEPT_TYPE,
            primaryCoding=primary_coding,
            name=name,
            aliases=aliases,
            mappings=mappings,
            extensions=extensions,
        )
        return merged_disease, final_ids
