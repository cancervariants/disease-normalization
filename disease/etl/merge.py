"""Create concept groups and merged records."""
from disease.database import Database
from disease.schemas import SourcePriority
from typing import Set, Dict
import logging
from timeit import default_timer as timer

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class Merge:
    """Handles record merging."""

    def __init__(self, database: Database):
        """Initialize Merge instance.

        :param Database database: db instance to use for record retrieval
            and creation.
        """
        self._database = database
        self._groups = []  # dict keying concept IDs to group Sets

    def create_merged_concepts(self, record_ids: Set[str]):
        """Create concept groups, generate merged concept records, and
        update database.

        :param Set[str] record_ids: concept identifiers from which groups
            should be generated.
        """
        # build groups
        logger.info('Generating record ID sets...')
        start = timer()
        for concept_id in record_ids:
            record = self._database.get_record_by_id(concept_id)
            other_ids = record['other_identifiers']
            self._groups.append((concept_id, set(other_ids + [concept_id])))
        end = timer()
        logger.debug(f'Built record ID sets in {end - start} seconds')

        # build merged concepts
        logger.info('Creating merged records and updating database...')
        start = timer()
        for record_id, group in self._groups:
            merged_record = self._generate_merged_record(group)
            self._database.add_record(merged_record, 'merger')
            merge_ref = merged_record['concept_id'].lower()
            for concept_id in group:
                self._database.update_record(concept_id, 'merge_ref',
                                             merge_ref)
        end = timer()
        logger.info("merged concept generation successful.")
        logger.debug(f'Generated and added concepts in {end - start} seconds)')

    def _generate_merged_record(self, record_id_set: Set[str]) -> Dict:
        """Generate merged record from provided concept ID group.
        Where attributes are sets, they should be merged, and where they are
        scalars, assign from the highest-priority source where that attribute
        is non-null.

        Priority is NCIt > Mondo.
        :param Set record_id_set: group of concept IDs
        :return: completed merged drug object to be stored in DB
        """
        records = []
        for record_id in record_id_set:
            record = self._database.get_record_by_id(record_id)
            if record:
                records.append(record)
            else:
                logger.error(f"Merge record generator could not retrieve "
                             f"record for {record_id} in {record_id_set}")

        def record_order(record):
            """Provide priority values of concepts for sort function."""
            src = record['src_name'].upper()
            if src in SourcePriority.__members__:
                source_rank = SourcePriority[src].value
            else:
                raise Exception(f"Prohibited source: {src} in concept_id "
                                f"{record['concept_id']}")
            return (source_rank, record['concept_id'])
        records.sort(key=record_order)

        merged_properties = {
            'concept_id': None,
            'aliases': set(),
            'xrefs': set()
        }
        set_fields = ['aliases', 'xrefs']
        scalar_fields = ['label', 'pediatric_disease']
        for record in records:
            for field in set_fields:
                merged_properties[field] |= set(record[field])
            if not merged_properties['concept_id']:
                merged_properties['concept_id'] = record['concept_id']
            else:
                merged_properties['concept_id'] += f"|{record['concept_id']}"

            for field in scalar_fields:
                if field not in merged_properties and field in record:
                    merged_properties[field] = record[field]

        for field in set_fields:
            field_value = merged_properties[field]
            if field_value:
                merged_properties[field] = list(field_value)
            else:
                del merged_properties[field]

        merged_properties['label_and_type'] = \
            f'{merged_properties["concept_id"].lower()}##merger'
        return merged_properties
