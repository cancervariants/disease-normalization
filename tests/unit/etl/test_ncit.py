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

from disease.database import AbstractDatabase
from disease.etl.ncit import NCIt
from disease.schemas import SourceName

fixtures = {
    "ncit:C3270": MappableConcept(
        id="ncit:C3270",
        conceptType="disease",
        primaryCoding=Coding(
            id="ncit:C3270",
            system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
            code=code(root="C3270"),
        ),
        name="Neuroblastoma",
        aliases=[
            "Neural Crest Tumor, Malignant",
            "Neuroblastoma (NBL)",
            "Neuroblastoma (Schwannian Stroma-poor)",
            "Neuroblastoma (Schwannian Stroma-Poor)",
            "NEUROBLASTOMA, MALIGNANT",
            "Neuroblastoma, NOS",
            "neuroblastoma",
        ],
        mappings=[
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C2751421",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C2751421"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="icdo:9500/3",
                    system="https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
                    code=code(root="9500/3"),
                ),
            ),
        ],
    ),
    "ncit:C2926": MappableConcept(
        id="ncit:C2926",
        name="Lung Non-Small Cell Carcinoma",
        conceptType="disease",
        primaryCoding=Coding(
            id="ncit:C2926",
            system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
            code=code(root="C2926"),
        ),
        aliases=[
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
        ],
        mappings=[
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
}

expected_dataset = DataSet(
    name="NCIt",
    version="25.08d",
    license=MappableConcept(
        name="CC BY 4.0",
        primaryCoding=Coding(
            code=code(root="CC-BY-4.0"),
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
    extensions=[
        Extension(name="data_url", value="https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/"),
        Extension(name="rdp_url", value="http://reusabledata.org/ncit.html"),
    ],
)


def test_ncit_etl(mock_db_class: type[AbstractDatabase], test_data_dir: Path):
    db = mock_db_class()
    etl = NCIt(db, test_data_dir / "ncit")
    etl.perform_etl(use_existing=True)

    added_records = db._added_records
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

    assert len(db._added_sources) == 1
    assert (
        deepdiff.DeepDiff(
            db._added_sources[SourceName.NCIT],
            expected_dataset,
            ignore_order=True,
        )
        == {}
    )
