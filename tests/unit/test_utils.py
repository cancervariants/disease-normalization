"""Test utils module"""

import pytest
from deepdiff import DeepDiff

from disease.database.database import AbstractDatabase
from disease.schemas import RecordType, SourceName
from disease.utils import get_term_mappings


@pytest.fixture(scope="module")
def test_db(null_database_class):
    return null_database_class(
        get_all_records={
            RecordType.IDENTITY: [
                {
                    "concept_id": "ncit:C185069",
                    "label": "Metastatic Hilar Cholangiocarcinoma",
                    "src_name": "NCIt",
                    "item_type": "identity",
                },
                {
                    "concept_id": "DOID:10348",
                    "label": "blepharophimosis",
                    "associated_with": [
                        "mesh:D016569",
                        "icd9.cm:374.46",
                        "icd10.cm:H02.52",
                        "umls:C0005744",
                        "gard:5932",
                    ],
                    "src_name": "DO",
                    "merge_ref": "mondo:0001008",
                    "item_type": "identity",
                },
                {
                    "concept_id": "ncit:C6610",
                    "label": "Stage IIA Osteosarcoma AJCC v7",
                    "aliases": [
                        "Stage IIA Osteosarcoma",
                        "Stage IIA Osteogenic Sarcoma",
                    ],
                    "associated_with": ["umls:C1336168"],
                    "src_name": "NCIt",
                    "item_type": "identity",
                },
                {
                    "concept_id": "mondo:0018648",
                    "label": "Keratocystic odontogenic tumor",
                    "aliases": [
                        "odontogenic keratocystoma",
                        "odontogenic Keratocyst",
                        "KTOC",
                    ],
                    "associated_with": [
                        "umls:C1708604",
                        "medgen:313330",
                        "orphanet:447777",
                    ],
                    "xrefs": ["ncit:C54302"],
                    "src_name": "Mondo",
                    "merge_ref": "mondo:0018648",
                    "oncologic_disease": True,
                    "item_type": "identity",
                },
            ],
            RecordType.MERGER: [
                {
                    "concept_id": "mondo:0008213",
                    "label": "pectus excavatum",
                    "aliases": [
                        "funnel chest",
                        "pectus excavatum",
                        "FUNNEL CHEST",
                        "pectus excavatum (disease)",
                    ],
                    "associated_with": [
                        "umls:C2051831",
                        "mesh:D005660",
                        "icd10.cm:Q67.6",
                        "medgen:781174",
                    ],
                    "xrefs": ["MIM:169300"],
                    "item_type": "merger",
                },
                {
                    "concept_id": "ncit:C40144",
                    "label": "Endometrial Mucinous Adenocarcinoma",
                    "aliases": [
                        "endometrium mucinous adenocarcinoma",
                        "Uterine Corpus Mucinous Adenocarcinoma",
                        "uterine mucinous carcinoma",
                        "uterine corpus mucinous adenocarcinoma",
                        "endometrial mucinous adenocarcinoma",
                        "uterine Corpus mucinous adenocarcinoma",
                    ],
                    "associated_with": [
                        "medgen:276939",
                        "umls:C1519859",
                        "efo:1000236",
                        "umls:C0854923",
                    ],
                    "xrefs": ["mondo:0002747", "oncotree:UMC", "DOID:3707"],
                    "oncologic_disease": True,
                    "item_type": "merger",
                },
                {
                    "concept_id": "ncit:C5063",
                    "label": "Endobronchial Lipoma",
                    "aliases": ["endobronchial lipoma"],
                    "associated_with": ["medgen:208874", "umls:C0852937"],
                    "xrefs": ["DOID:10183", "mondo:0000961"],
                    "oncologic_disease": True,
                    "item_type": "merger",
                },
                {
                    "concept_id": "oncotree:CAEXPA",
                    "label": "Carcinoma ex Pleomorphic Adenoma",
                    "src_name": "OncoTree",
                    "oncologic_disease": True,
                    "item_type": "identity",
                },
            ],
        }
    )


def test_get_term_mappings_ncit(test_db: AbstractDatabase):
    results = list(get_term_mappings(test_db, SourceName.NCIT))

    ncit_mappings_fixture = [
        {
            "concept_id": "ncit:C185069",
            "label": "Metastatic Hilar Cholangiocarcinoma",
            "xrefs": [],
            "aliases": [],
        },
        {
            "concept_id": "ncit:C6610",
            "label": "Stage IIA Osteosarcoma AJCC v7",
            "xrefs": ["umls:C1336168"],
            "aliases": [
                "Stage IIA Osteosarcoma",
                "Stage IIA Osteogenic Sarcoma",
            ],
        },
    ]
    diff = DeepDiff(ncit_mappings_fixture, results, ignore_order=True)
    assert diff == {}


def test_get_term_mappings_merger(test_db: AbstractDatabase):
    results = list(get_term_mappings(test_db, scope=RecordType.MERGER))

    fixture = [
        {
            "concept_id": "mondo:0008213",
            "label": "pectus excavatum",
            "aliases": [
                "funnel chest",
                "pectus excavatum",
                "FUNNEL CHEST",
                "pectus excavatum (disease)",
            ],
            "xrefs": [
                "umls:C2051831",
                "mesh:D005660",
                "icd10.cm:Q67.6",
                "medgen:781174",
                "MIM:169300",
            ],
        },
        {
            "concept_id": "ncit:C40144",
            "label": "Endometrial Mucinous Adenocarcinoma",
            "aliases": [
                "endometrium mucinous adenocarcinoma",
                "Uterine Corpus Mucinous Adenocarcinoma",
                "uterine mucinous carcinoma",
                "uterine corpus mucinous adenocarcinoma",
                "endometrial mucinous adenocarcinoma",
                "uterine Corpus mucinous adenocarcinoma",
            ],
            "xrefs": [
                "medgen:276939",
                "umls:C1519859",
                "efo:1000236",
                "umls:C0854923",
                "mondo:0002747",
                "oncotree:UMC",
                "DOID:3707",
            ],
        },
        {
            "concept_id": "ncit:C5063",
            "label": "Endobronchial Lipoma",
            "aliases": ["endobronchial lipoma"],
            "xrefs": ["medgen:208874", "umls:C0852937", "DOID:10183", "mondo:0000961"],
        },
        {
            "concept_id": "oncotree:CAEXPA",
            "label": "Carcinoma ex Pleomorphic Adenoma",
            "aliases": [],
            "xrefs": [],
        },
    ]
    diff = DeepDiff(fixture, results, ignore_order=True)
    assert diff == {}


def test_get_term_mappings_cancer(test_db: AbstractDatabase):
    results = list(
        get_term_mappings(test_db, scope=RecordType.IDENTITY, cancer_only=True)
    )
    assert len(results) == 1
