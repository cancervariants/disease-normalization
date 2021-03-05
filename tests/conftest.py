"""Pytest test config tools."""
from disease.database import Database
from disease import PROJECT_ROOT
from typing import Dict, Any, Optional, List
import json
import pytest


@pytest.fixture(scope='module')
def compare_merged_records():
    """Check that records are identical."""

    def compare_merged_records(actual, fixture):
        if 'concept_ids' in actual:  # record as displayed externally
            assert 'concept_ids' in fixture
            assert 'concept_id' not in actual and 'concept_id' not in fixture
            assert set(actual['concept_ids']) == set(fixture['concept_ids'])
        elif 'concept_id' in actual:  # record as stored internally
            assert 'concept_id' in fixture
            assert 'concept_ids' not in fixture
            assert actual['concept_id'] == fixture['concept_id']
            assert ('other_ids' in actual) == ('other_ids' in fixture)

            assert actual['label_and_type'] == fixture['label_and_type']
            assert actual['item_type'] == fixture['item_type']

            if 'other_ids' in actual:
                assert set(actual['other_ids']) == set(fixture['other_ids'])

        assert ('label' in actual) == ('label' in fixture)
        if 'label' in actual or 'label' in fixture:
            assert actual['label'] == fixture['label']

        assert ('aliases' in actual) == ('aliases' in fixture)
        if 'aliases' in actual or 'aliases' in fixture:
            assert set(actual['aliases']) == set(fixture['aliases'])

        assert ('xrefs' in actual) == ('xrefs' in fixture)
        if 'xrefs' in actual or 'xrefs' in fixture:
            assert set(actual['xrefs']) == set(fixture['xrefs'])

        assert ('pediatric_disease' in actual) == \
            ('pediatric_disease' in fixture)
        if 'pediatric_disease' in actual or 'pediatric_disease' in fixture:
            assert actual['pediatric_disease'] == fixture['pediatric_disease']

    return compare_merged_records


@pytest.fixture(scope='module')
def mock_database():
    """Return MockDatabase object."""

    class MockDatabase(Database):
        """Mock database object to use in test cases."""

        def __init__(self):
            """Initialize mock database object. This class's method's shadow the
            actual Database class methods.

            `self.records` loads preexisting DB items.
            `self.added_records` stores add record requests, with the
            concept_id as the key and the complete record as the value.
            `self.updates` stores update requests, with the concept_id as the
            key and the updated attribute and new value as the value.
            """
            infile = PROJECT_ROOT / '..' / 'tests' / 'unit' / 'data' / 'diseases.json'  # noqa: E501
            with open(infile, 'r') as f:
                records_json = json.load(f)
            self.records = {}
            for record in records_json:
                self.records[record['label_and_type']] = {
                    record['concept_id']: record
                }
            self.added_records: Dict[str, Dict[Any, Any]] = {}
            self.updates: Dict[str, Dict[Any, Any]] = {}
            meta = PROJECT_ROOT / '..' / 'tests' / 'unit' / 'data' / 'metadata.json'  # noqa: E501
            with open(meta, 'r') as f:
                meta_json = json.load(f)
            self.cached_sources = {}
            for src in meta_json:
                name = src['src_name']
                self.cached_sources[name] = src
                del self.cached_sources[name]['src_name']

        def get_record_by_id(self, record_id: str,
                             case_sensitive: bool = True,
                             merge: bool = False) -> Optional[Dict]:
            """Fetch record corresponding to provided concept ID.

            :param str concept_id: concept ID for disease record
            :param bool case_sensitive: if true, performs exact lookup, which
                is more efficient. Otherwise, performs filter operation, which
                doesn't require correct casing.
            :param bool merge: if true, retrieve merged record
            :return: complete record, if match is found; None otherwise
            """
            if merge:
                label_and_type = f'{record_id.lower()}##merger'
            else:
                label_and_type = f'{record_id.lower()}##identity'
            record_lookup = self.records.get(label_and_type, None)
            if record_lookup:
                if case_sensitive:
                    record = record_lookup.get(record_id, None)
                    if record:
                        return record.copy()
                    else:
                        return None
                elif record_lookup.values():
                    return list(record_lookup.values())[0].copy()
            return None

        def get_records_by_type(self, query: str,
                                match_type: str) -> List[Dict]:
            """Retrieve records for given query and match type.

            :param query: string to match against
            :param str match_type: type of match to look for. Should be one
                of "alias" or "label" (use get_record_by_id for
                concept ID lookup)
            :return: list of matching records. Empty if lookup fails.
            """
            assert match_type in ('alias', 'label')
            label_and_type = f'{query}##{match_type.lower()}'
            records_lookup = self.records.get(label_and_type, None)
            if records_lookup:
                return [v.copy() for v in records_lookup.values()]
            else:
                return []

        def get_merged_record(self, merge_ref) -> Optional[Dict]:
            """Fetch merged record from given reference.

            :param str merge_ref: key for merged record, formated as a string
                of grouped concept IDs separated by vertical bars, ending with
                `##merger`. Must be correctly-cased.
            :return: complete merged record if lookup successful, None
                otherwise
            """
            record_lookup = self.records.get(merge_ref, None)
            if record_lookup:
                vals = list(record_lookup.values())
                if vals:
                    return vals[0].copy()
            return None

        def add_record(self, record: Dict, record_type: str):
            """Store add record request sent to database.

            :param Dict record: record (of any type) to upload. Must include
                `concept_id` key. If record is of the `identity` type, the
                concept_id must be correctly-cased.
            :param str record_type: ignored by this function
            """
            self.added_records[record['concept_id']] = record

        def update_record(self, concept_id: str, attribute: str,
                          new_value: Any):
            """Store update request sent to database.

            :param str concept_id: record to update
            :param str field: name of field to update
            :parm str new_value: new value
            """
            assert f'{concept_id.lower()}##identity' in self.records
            self.updates[concept_id] = {attribute: new_value}

    return MockDatabase
