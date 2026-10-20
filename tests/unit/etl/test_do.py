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
from disease.etl.do import DO
from disease.schemas import SourceName

fixtures = {
    "DOID:769": MappableConcept(
        id="DOID:769",
        conceptType="disease",
        primaryCoding=Coding(
            id="DOID:769",
            system="https://disease-ontology.org/?id=",
            code=code(root="DOID:769"),
        ),
        name="neuroblastoma",
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
                    id="gard:7185",
                    system="https://rarediseases.info.nih.gov",
                    code=code(root="7185"),
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
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
    "DOID:5695": MappableConcept(
        id="DOID:5695",
        primaryCoding=Coding(
            id="DOID:5695",
            system="https://disease-ontology.org/?id=",
            code=code(root="DOID:5695"),
        ),
        name="childhood liposarcoma",
        conceptType="disease",
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
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0279984",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0279984"),
                ),
            ),
        ],
        aliases=["pediatric liposarcoma"],
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
    "DOID:1703": MappableConcept(
        id="DOID:1703",
        primaryCoding=Coding(
            id="DOID:1703",
            system="https://disease-ontology.org/?id=",
            code=code(root="DOID:1703"),
        ),
        conceptType="disease",
        name="Richter's syndrome",
        aliases=["Richter syndrome"],
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
                    id="gard:7578",
                    system="https://rarediseases.info.nih.gov",
                    code=code(root="7578"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="icd10.cm:C91.1",
                    system="https://www.cdc.gov/nchs/icd/icd-10-cm/index.html",
                    code=code(root="C91.1"),
                ),
            ),
        ],
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
    # test for application of rules
    "DOID:6032": MappableConcept(
        id="DOID:6032",
        primaryCoding=Coding(
            id="DOID:6032",
            system="https://disease-ontology.org/?id=",
            code=code(root="DOID:6032"),
        ),
        conceptType="disease",
        name="juvenile type testicular granulosa cell tumor",
        aliases=[
            "Juvenile granulosa cell tumor",
            "Juvenile granulosa cell tumour",
            "Juvenile type Granulosa cell tumor",
            "Juvenile type Granulosa cell tumour",
            "juvenile type granulosa cell neoplasm",
            "juvenile type testicular granulosa cell tumour",
        ],
        mappings=[
            ConceptMapping(
                relation=Relation.EXACT_MATCH,
                coding=Coding(
                    id="ncit:C39947",
                    system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    code=code(root="C39947"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C0334403",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C0334403"),
                ),
            ),
            ConceptMapping(
                relation=Relation.RELATED_MATCH,
                coding=Coding(
                    id="umls:C1515285",
                    system="https://www.nlm.nih.gov/research/umls/index.html",
                    code=code(root="C1515285"),
                ),
            ),
        ],
        extensions=[Extension(name="oncologic_disease", value=True)],
    ),
}

expected_dataset = DataSet(
    name="DO",
    version="20250627",
    license=MappableConcept(
        name="CC0 1.0",
        primaryCoding=Coding(
            code=code(root="CC0 1.0"),
            system="https://spdx.org/licenses/",
            iris=[
                iriReference(
                    root="https://creativecommons.org/publicdomain/zero/1.0/legalcode"
                )
            ],
        ),
        extensions=[
            Extension(
                name="license_attributes",
                value={
                    "non_commercial": False,
                    "share_alike": False,
                    "attribution": False,
                },
            ),
        ],
    ),
    extensions=[
        Extension(
            name="data_url",
            value="http://www.obofoundry.org/ontology/doid.html",
        ),
    ],
)


def test_do_etl(mock_etl_db: AbstractDatabase, test_data_dir: Path):
    etl = DO(mock_etl_db, test_data_dir / "do")
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
            mock_etl_db._added_sources[SourceName.DO],
            expected_dataset,
            ignore_order=True,
        )
        == {}
    )
