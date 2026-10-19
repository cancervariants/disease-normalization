from pathlib import Path

import deepdiff
from ga4gh.core.models import (
    Coding,
    ConceptMapping,
    Extension,
    MappableConcept,
    Relation,
    code,
    iriReference,
)
from ga4gh.va_spec.base import DataSet

from disease.database.database import AbstractDatabase
from disease.etl.oncotree import OncoTree
from disease.schemas import SourceName

fixtures = {
    "oncotree:ICPN": MappableConcept(
        id="oncotree:ICPN",
        name="Intracholecystic Papillary Neoplasm",
        primaryCoding=Coding(
            id="oncotree:ICPN",
            code="ICPN",
            system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
        ),
        conceptType="disease",
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
    "oncotree:NSCLC": MappableConcept(
        id="oncotree:NSCLC",
        name="Non-Small Cell Lung Cancer",
        conceptType="disease",
        primaryCoding=Coding(
            id="oncotree:NSCLC",
            code="NSCLC",
            system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
        ),
        extensions=[Extension(name="oncologic_disease", value=True)],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C2926",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C2926"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0007131",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0007131"),
                ),
            ),
        ],
    ),
    "oncotree:NBL": MappableConcept(
        id="oncotree:NBL",
        conceptType="disease",
        primaryCoding=Coding(
            id="oncotree:NBL",
            code="NBL",
            system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
        ),
        name="Neuroblastoma",
        extensions=[Extension(name="oncologic_disease", value=True)],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C3270",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C3270"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0027819",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0027819"),
                ),
            ),
        ],
    ),
}
expected_dataset = DataSet(
    name="OncoTree",
    version="20211102",
    extensions=[
        Extension(
            name="data_url",
            value="http://oncotree.mskcc.org/#/home?tab=api",
        ),
    ],
    license=MappableConcept(
        name="CC BY 4.0",
        primaryCoding=Coding(
            code=code(root="CC BY 4.0"),
            system="https://spdx.org/licenses/",
            iris=[
                iriReference(
                    root="https://creativecommons.org/licenses/by/4.0/legalcode"
                )
            ],
        ),
        extensions=[
            Extension(
                name="license_attributes",
                value={
                    "non_commercial": False,
                    "share_alike": False,
                    "attribution": True,
                },
            ),
        ],
    ),
)


def test_oncotree_etl(mock_etl_db: AbstractDatabase, test_data_dir: Path):
    etl = OncoTree(mock_etl_db, test_data_dir / "oncotree")
    etl.perform_etl(use_existing=True)

    added_records = mock_etl_db._added_records
    for id_key, expected in fixtures.items():
        assert (
            deepdiff.DeepDiff(
                added_records[id_key],
                expected,
                ignore_order=True,
                report_repetition=True,
            )
            == {}
        )

    assert len(mock_etl_db._added_sources) == 1
    assert (
        deepdiff.DeepDiff(
            mock_etl_db._added_sources[SourceName.ONCOTREE],
            expected_dataset,
            ignore_order=True,
        )
        == {}
    )
