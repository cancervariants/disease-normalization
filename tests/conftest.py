"""Pytest test config tools."""
from disease.database import Database
from typing import Dict, Any, Optional, List
import json
import pytest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def compare_records():
    """Provide compare_records method to test classes"""
    def compare_records(actual_record: Dict, fixture_record: Dict):
        """Check that identity records are identical."""
        assert actual_record['concept_id'] == fixture_record['concept_id']
        assert ('label' in actual_record.keys()) == ('label' in fixture_record.keys())  # noqa: E501
        if 'label' in actual_record or 'label' in fixture_record:
            assert actual_record['label'] == fixture_record['label']
        assert ('aliases' in actual_record.keys()) == ('aliases' in fixture_record.keys())  # noqa: E501
        if 'aliases' in actual_record or 'aliases' in fixture_record:
            assert set(actual_record['aliases']) == set(fixture_record['aliases'])  # noqa: E501
        assert ('other_identifiers' in actual_record.keys()) == ('other_identifiers' in fixture_record.keys())  # noqa: E501
        if 'other_identifiers' in actual_record or 'other_identifiers' in fixture_record:  # noqa: E501
            assert set(actual_record['other_identifiers']) == set(fixture_record['other_identifiers'])  # noqa: E501
        assert ('xrefs' in actual_record.keys()) == ('xrefs' in fixture_record.keys())  # noqa: E501
        if 'xrefs' in actual_record or 'xrefs' in fixture_record:
            assert set(actual_record['xrefs']) == set(fixture_record['xrefs'])
    return compare_records


@pytest.fixture(scope='module')
def provide_root():
    """Provide TEST_ROOT value to test cases."""
    return TEST_ROOT


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
            infile = TEST_ROOT / 'tests' / 'unit' / 'data' / 'diseases.json'
            with open(infile, 'r') as f:
                records_json = json.load(f)
            self.records = {}
            for record in records_json:
                self.records[record['label_and_type']] = {
                    record['concept_id']: record
                }
            self.added_records: Dict[str, Dict[Any, Any]] = {}
            self.updates: Dict[str, Dict[Any, Any]] = {}
            meta = TEST_ROOT / 'tests' / 'unit' / 'data' / 'metadata.json'
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
            record_lookup_sk = self.records.get(label_and_type)
            if record_lookup_sk:
                if case_sensitive:
                    record = record_lookup_sk.get(record_id)
                    if record:
                        return record.copy()
                    else:
                        return None
                elif record_lookup_sk.values():
                    return list(record_lookup_sk.values())[0].copy()
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
