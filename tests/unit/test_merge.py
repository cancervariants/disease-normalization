"""Test merged record generation."""
import pytest
from disease.etl.merge import Merge
from typing import Dict


@pytest.fixture(scope='module')
def merge_handler(mock_database):
    """Provide Merge instance to test cases."""
    class MergeHandler():
        def __init__(self):
            self.merge = Merge(mock_database())

        def get_merge(self):
            return self.merge

        def create_merged_concepts(self, record_ids):
            return self.merge.create_merged_concepts(record_ids)

        def get_added_records(self):
            return self.merge._database.added_records

        def get_updates(self):
            return self.merge._database.updates

        def generate_merged_record(self, record_id_set):
            return self.merge._generate_merged_record(record_id_set)

    return MergeHandler()


def compare_merged_records(actual_record: Dict, fixture_record: Dict):
    """Check that records are identical."""
    assert actual_record['concept_id'] == fixture_record['concept_id']
    assert actual_record['label_and_type'] == fixture_record['label_and_type']
    assert ('label' in actual_record) == ('label' in fixture_record)
    if 'label' in actual_record or 'label' in fixture_record:
        assert actual_record['label'] == fixture_record['label']
    assert ('aliases' in actual_record) == ('aliases' in fixture_record)
    if 'aliases' in actual_record or 'aliases' in fixture_record:
        assert set(actual_record['aliases']) == set(fixture_record['aliases'])
    assert ('xrefs' in actual_record) == ('xrefs' in fixture_record)
    if 'xrefs' in actual_record or 'xrefs' in fixture_record:
        assert set(actual_record['xrefs']) == set(fixture_record['xrefs'])
    assert ('pediatric_disease' in actual_record) == \
        ('pediatric_disease' in fixture_record)
    if 'pediatric_disease' in actual_record or \
            'pediatric_disease' in fixture_record:
        assert set(actual_record['pediatric_disease']) == \
            set(fixture_record['pediatric_disease'])


@pytest.fixture(scope='module')
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return {
        "label_and_type": "mondo:0005072|ncit:c3270|doid:769##merger",
        "concept_id": "mondo:0005072|ncit:C3270|DOID:769##merger",
        "label": "Neuroblastoma",
        "aliases": [
            "neuroblastoma",
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "Neuroblastoma, NOS",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma (NBL)"
            "neural Crest tumor, malignant",
            "neuroblastoma, malignant"
        ],
        "xrefs": [
            "umls:C0027819",
            "icd.o:9500/3"
            "efo:0000621",
            "gard:0007185",
            "icd:C74.9",
            "icd.o:9500/3",
            "mesh:D009447",
            "meddra:10029260",
            "nifstd:birnlex_12631",
            "oncotree:NBL",
            "orphanet:635",
            "umls:CN205405"
        ],
        "pediatric": None
    }
