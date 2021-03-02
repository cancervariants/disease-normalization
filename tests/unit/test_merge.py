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
        assert actual_record['pediatric_disease'] == \
            fixture_record['pediatric_disease']


@pytest.fixture(scope='module')
def neuroblastoma():
    """Create neuroblastoma fixture."""
    return {
        "label_and_type": "ncit:c3270|mondo:0005072|oncotree:nbl|doid:769##merger",  # noqa: E501
        "concept_id": "ncit:C3270|mondo:0005072|oncotree:NBL|DOID:769",
        "label": "Neuroblastoma",
        "aliases": [
            "neuroblastoma",
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "Neuroblastoma, NOS",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma (NBL)",
            "neural Crest tumor, malignant",
            "neuroblastoma, malignant"
        ],
        "xrefs": [
            "umls:C0027819",
            "icd.o:9500/3",
            "efo:0000621",
            "gard:7185",
            "gard:0007185",
            "icd:C74.9",
            "icd.o:9500/3",
            "icd.o:M9500/3",
            "mesh:D009447",
            "meddra:10029260",
            "nifstd:birnlex_12631",
            "orphanet:635",
            "umls:CN205405"
        ],
        "pediatric": None
    }


@pytest.fixture(scope='module')
def lnscc():
    """Create lung non small cell carcinoma fixture"""
    return {
        "label_and_type": "ncit:c2926|mondo:0005233|oncotree:nsclc|doid:3908##merger",  # noqa: E501
        "concept_id": "ncit:C2926|mondo:0005233|oncotree:NSCLC|DOID:3908",
        "label": "Lung Non-Small Cell Carcinoma",
        "aliases": [
            "Non Small Cell Lung Cancer NOS",
            "Non-Small Cell Lung Cancer",
            "Non-Small Cell Cancer of the Lung",
            "NSCLC",
            "non-small cell lung cancer",
            "Non-Small Cell Carcinoma of the Lung",
            "Non-Small Cell Cancer of Lung",
            "Non-small cell lung cancer, NOS",
            "Non-Small Cell Carcinoma of Lung",
            "NSCLC - Non-Small Cell Lung Cancer",
            "Non-Small Cell Lung Carcinoma",
            "NSCLC - non-small cell lung cancer",
            "non-small cell lung carcinoma",
            "non-small cell carcinoma of lung",
            "non-small cell carcinoma of the lung",
            "non-small cell cancer of lung",
            "non-small cell cancer of the lung",
        ],
        "xrefs": [
            "umls:C0007131",
            "mesh:D002289",
            "umls:C0007131",
            "efo:0003060",
            "icd10:C34",
            "kegg.disease:05223",
            "HP:0030358"
        ],
        "item_type": "merger"
    }


@pytest.fixture(scope='module')
def richter():
    """Create Richter Syndrome fixture"""
    return {
        "label_and_type": "ncit:c35424|mondo:0002083|doid:1703##merger",
        "concept_id": "ncit:C35424|mondo:0002083|DOID:1703",
        "label": "Richter Syndrome",
        "aliases": [
            "Richter's Syndrome",
            "Richter syndrome",
            "Richter transformation",
            "Richter's Transformation",
            "Richter's syndrome",
            "Richter's transformation"
        ],
        "xrefs": [
            "umls:C0349631",
            "icd:C91.1",
            "gard:0007578",
            "gard:7578",
            "icd10.cm:C91.1"
        ],
        "item_type": "merger"
    }


@pytest.fixture(scope='module')
def ped_liposarcoma():
    """Create pediatric liposarcoma fixture."""
    return {
        "label_and_type": "ncit:c8091|mondo:0003587|doid:5695##merger",
        "concept_id": "ncit:C8091|mondo:0003587|DOID:5695",
        "label": "Childhood Liposarcoma",
        "aliases": [
            "Liposarcoma",
            "Pediatric Liposarcoma",
            "childhood liposarcoma",
            "liposarcoma"
        ],
        "xrefs": ["umls:C0279984"],
        "pediatric_disease": True,
        "item_type": "merger"
    }


@pytest.fixture(scope='module')
def teratoma():
    """Create fixture for adult cystic teratoma."""
    return {
        "label_and_type": "ncit:c9012|mondo:0004099|doid:7079##merger",
        "concept_id": "ncit:C9012|mondo:0004099|DOID:7079",
        "label": "Adult Cystic Teratoma",
        "aliases": ["Adult cystic teratoma", "cystic teratoma of adults"],
        "xrefs": ["icd.o:9080/0", "umls:C1368888"],
        "item_type": "merger",
    }


@pytest.fixture(scope='module')
def mafd2():
    """Create a fixture for major affective disorder 2. Tests whether a
    deprecated DO reference is filtered out.
    """
    return {
        "label_and_type": "mondo:0010648##merger",
        "item_type": "merger",
        "concept_id": "mondo:0010648",
        "label": "major affective disorder 2",
        "aliases": [
            "MAFD2"
        ],
        "xrefs": [
            "mesh:C564108",
            "omim:309200"
        ]
    }


@pytest.fixture(scope='module')
def record_id_groups():
    """Fixture for concept ID group input."""
    return {
        'neuroblastoma': [
            "ncit:C3270", "mondo:0005072", "DOID:769", "oncotree:NBL"
        ],
        'lnscc': [
            "ncit:C2926", "mondo:0005233", "DOID:3908", "oncotree:NSCLC"
        ],
        'richter': [
            "ncit:C35424", "mondo:0002083", "DOID:1703"
        ],
        'ped_liposarcoma': [
            "ncit:C8091", "mondo:0003587", "DOID:5695"
        ],
        'teratoma': [
            "ncit:C9012", "mondo:0004099", "DOID:7079"
        ],
        'mafd2': ["mondo:0010648", "DOID:0080221"]
    }


def test_generate_merged_record(merge_handler, record_id_groups, neuroblastoma,
                                lnscc, richter, ped_liposarcoma, teratoma,
                                mafd2):
    """Test generation of individual merged record."""
    neuroblastoma_ids = record_id_groups['neuroblastoma']
    response, r_ids = merge_handler.generate_merged_record(neuroblastoma_ids)
    assert set(r_ids) == set(neuroblastoma_ids)
    compare_merged_records(response, neuroblastoma)

    lnscc_ids = record_id_groups['lnscc']
    response, r_ids = merge_handler.generate_merged_record(lnscc_ids)
    assert set(r_ids) == set(lnscc_ids)
    compare_merged_records(response, lnscc)

    richter_ids = record_id_groups['richter']
    response, r_ids = merge_handler.generate_merged_record(richter_ids)
    assert set(r_ids) == set(richter_ids)
    compare_merged_records(response, richter)

    ped_liposarcoma_ids = record_id_groups['ped_liposarcoma']
    response, r_ids = merge_handler.generate_merged_record(ped_liposarcoma_ids)
    assert set(r_ids) == set(ped_liposarcoma_ids)
    compare_merged_records(response, ped_liposarcoma)

    teratoma_ids = record_id_groups['teratoma']
    response, r_ids = merge_handler.generate_merged_record(teratoma_ids)
    assert set(r_ids) == set(teratoma_ids)
    compare_merged_records(response, teratoma)

    mafd2_ids = record_id_groups['mafd2']
    response, r_ids = merge_handler.generate_merged_record(mafd2_ids)
    assert set(r_ids) == {"mondo:0010648"}
    compare_merged_records(response, mafd2)


def test_create_merged_concepts(merge_handler, record_id_groups, neuroblastoma,
                                lnscc, richter, ped_liposarcoma, teratoma,
                                mafd2):
    """Test end-to-end creation and upload of merged concepts."""
    mondo_ids = [
        "mondo:0005072",
        "mondo:0005233",
        "mondo:0002083",
        "mondo:0004099",
        "mondo:0003587",
        "mondo:0010648"
    ]
    merge_handler.create_merged_concepts(mondo_ids)

    # check merged record generation and storage
    added_records = merge_handler.get_added_records()
    assert len(added_records) == 6
    neuroblastoma_id = neuroblastoma['concept_id']
    assert neuroblastoma_id in added_records
    compare_merged_records(added_records[neuroblastoma_id],
                           neuroblastoma)
    lnscc_id = lnscc['concept_id']
    assert lnscc_id in added_records
    compare_merged_records(added_records[lnscc_id],
                           lnscc)
    richter_id = richter['concept_id']
    assert richter_id in added_records
    compare_merged_records(added_records[richter_id],
                           richter)
    ped_liposarcoma_id = ped_liposarcoma['concept_id']
    assert ped_liposarcoma_id in added_records
    compare_merged_records(added_records[ped_liposarcoma_id],
                           ped_liposarcoma)
    teratoma_id = teratoma['concept_id']
    assert teratoma_id in added_records
    compare_merged_records(added_records[teratoma_id],
                           teratoma)
    mafd2_id = mafd2['concept_id']
    assert mafd2_id in added_records
    compare_merged_records(added_records[mafd2_id],
                           mafd2)
