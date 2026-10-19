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
from disease.etl.mondo import Mondo
from disease.schemas import SourceName

fixtures = {
    "mondo:0005072": MappableConcept(
        id="mondo:0005072",
        conceptType="disease",
        primaryCoding=Coding(
            code="MONDO:0005072",
            id="MONDO_0005072",
            system="https://purl.obolibrary.org/obo/",
        ),
        name="neuroblastoma",
        aliases=[
            "NB",
            "neuroblastoma",
            "neural Crest tumor, malignant",
            "neuroblastoma (Schwannian Stroma-poor)",
            "neuroblastoma, malignant",
        ],
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
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="DOID:769",
                    system="https://disease-ontology.org/?id=",
                    code=code(root="DOID:769"),
                ),
            ),
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="oncotree:NBL",
                    system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
                    code=code(root="NBL"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="orphanet:635",
                    system="https://www.orpha.net",
                    code=code(root="635"),
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
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="efo:0000621",
                    system="http://www.ebi.ac.uk/efo/EFO_",
                    code=code(root="0000621"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="mesh:D009447",
                    system="https://meshb.nlm.nih.gov/record/ui?ui=",
                    code=code(root="D009447"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="medgen:18012",
                    system="https://www.ncbi.nlm.nih.gov/medgen/",
                    code=code(root="18012"),
                ),
            ),
        ],
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
    "mondo:0002083": MappableConcept(
        id="mondo:0002083",
        name="Richter syndrome",
        conceptType="disease",
        primaryCoding=Coding(
            code="MONDO:0002083",
            id="MONDO_0002083",
            system="https://purl.obolibrary.org/obo/",
        ),
        aliases=[
            "Richter syndrome",
            "Richter's syndrome",
            "Richter transformation",
            "Richter's transformation",
        ],
        extensions=[Extension(name="oncologic_disease", value=True)],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C35424",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C35424"),
                ),
            ),
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="DOID:1703",
                    system="https://disease-ontology.org/?id=",
                    code=code(root="DOID:1703"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0349631",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0349631"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="medgen:91159",
                    system="https://www.ncbi.nlm.nih.gov/medgen/",
                    code=code(root="91159"),
                ),
            ),
        ],
    ),
    "mondo:0003587": MappableConcept(
        id="mondo:0003587",
        primaryCoding=Coding(
            code="MONDO:0003587",
            id="MONDO_0003587",
            system="https://purl.obolibrary.org/obo/",
        ),
        conceptType="disease",
        name="pediatric liposarcoma",
        aliases=[
            "pediatric liposarcoma",
            "childhood liposarcoma",
            "liposarcoma",
        ],
        extensions=[
            Extension(name="oncologic_disease", value=True),
            Extension(name="pediatric_disease", value=True),
        ],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C8091",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C8091"),
                ),
            ),
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="DOID:5695",
                    system="https://disease-ontology.org/?id=",
                    code=code(root="DOID:5695"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0279984",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0279984"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="medgen:83580",
                    system="https://www.ncbi.nlm.nih.gov/medgen/",
                    code=code(root="83580"),
                ),
            ),
        ],
    ),
    "mondo:0004099": MappableConcept(
        id="mondo:0004099",
        primaryCoding=Coding(
            code="MONDO:0004099",
            id="MONDO_0004099",
            system="https://purl.obolibrary.org/obo/",
        ),
        conceptType="disease",
        name="adult cystic teratoma",
        aliases=["cystic teratoma of adults", "adult cystic teratoma"],
        extensions=[Extension(name="oncologic_disease", value=True)],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C9012",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C9012"),
                ),
            ),
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="DOID:7079",
                    system="https://disease-ontology.org/?id=",
                    code=code(root="DOID:7079"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C1368888",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C1368888"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="medgen:235084",
                    system="https://www.ncbi.nlm.nih.gov/medgen/",
                    code=code(root="235084"),
                ),
            ),
        ],
    ),
    "mondo:0005233": MappableConcept(
        id="mondo:0005233",
        primaryCoding=Coding(
            code="MONDO:0005233",
            id="MONDO_0005233",
            system="https://purl.obolibrary.org/obo/",
        ),
        conceptType="disease",
        name="non-small cell lung carcinoma",
        aliases=[
            "NSCLC - non-small cell lung cancer",
            "non-small cell lung carcinoma (disease)",
            "non-small cell carcinoma of lung",
            "non-small cell carcinoma of the lung",
            "non-small cell cancer of lung",
            "non-small cell lung cancer",
            "non-small cell cancer of the lung",
            "NSCLC",
            "non-small cell lung carcinoma",
        ],
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
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="DOID:3908",
                    system="https://disease-ontology.org/?id=",
                    code=code(root="DOID:3908"),
                ),
            ),
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="oncotree:NSCLC",
                    system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
                    code=code(root="NSCLC"),
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
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="efo:0003060",
                    system="http://www.ebi.ac.uk/efo/EFO_",
                    code=code(root="0003060"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="mesh:D002289",
                    system="https://meshb.nlm.nih.gov/record/ui?ui=",
                    code=code(root="D002289"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="medgen:40104",
                    system="https://www.ncbi.nlm.nih.gov/medgen/",
                    code=code(root="40104"),
                ),
            ),
        ],
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
}

expected_dataset = DataSet(
    name="Mondo",
    version="20251104",
    extensions=[
        Extension(
            name="data_url",
            value="https://mondo.monarchinitiative.org/pages/download/",
        ),
        Extension(name="rdp_url", value="http://reusabledata.org/monarch.html"),
    ],
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
)


def test_mondo_etl(mock_etl_db: AbstractDatabase, test_data_dir: Path):
    etl = Mondo(mock_etl_db, test_data_dir / "mondo")
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
            mock_etl_db._added_sources[SourceName.MONDO],
            expected_dataset,
            ignore_order=True,
        )
        == {}
    )
