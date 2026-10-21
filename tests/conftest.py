"""Pytest test config tools."""

import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
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

from disease.config import get_config
from disease.database.database import AWS_ENV_VAR_NAME, AbstractDatabase, create_db
from disease.etl.base import Base
from disease.query import QueryHandler
from disease.schemas import RecordType, RefType, SourceMeta, SourceName

_logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add custom commands to pytest invocation.
    See https://docs.pytest.org/en/7.1.x/reference/reference.html#parser
    """
    parser.addoption(
        "--verbose-logs",
        action="store_true",
        default=False,
        help="show noisy module logs",
    )


def pytest_configure(config):
    """Configure pytest setup."""
    if not config.getoption("--verbose-logs"):
        logging.getLogger("botocore").setLevel(logging.ERROR)
        logging.getLogger("boto3").setLevel(logging.ERROR)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide Path instance pointing to test data directory"""
    return Path(__file__).parent / "data"


def pytest_sessionstart():
    """Wipe DB before testing if in test environment."""
    if get_config().test:
        if os.environ.get(AWS_ENV_VAR_NAME):
            msg = f"Cannot have both DISEASE_NORM_TEST and {AWS_ENV_VAR_NAME} set."
            raise AssertionError(msg)
        db = create_db()
        db.drop_db()
        db.initialize_db()


@pytest.fixture(scope="session")
def is_test_env():
    """If true, currently in test environment (i.e. okay to overwrite DB). Downstream
    users should also make sure to check if in a production environment.

    Provided here to be accessible directly within test modules.
    """
    return get_config().test


@pytest.fixture(scope="module")
def database():
    """Provide a database instance to be used by tests."""
    db = create_db()
    yield db
    db.close_connection()


@pytest.fixture(scope="module")
def test_source(database: AbstractDatabase, is_test_env: bool, test_data_dir: Path):
    """Provide query endpoint for testing sources. If DISEASE_NORM_TEST is set, will try to
    load DB from test data.

    :param database: test database instance
    :param is_test_env: if true, load from test data
    :return: factory function that takes an ETL class instance and returns a query
    endpoint.
    """

    def test_source_factory(EtlClass: Base):  # noqa: N803
        if is_test_env:
            _logger.debug("Reloading DB with data from %s", test_data_dir)
            test_class = EtlClass(database, test_data_dir / EtlClass.__name__.lower())
            test_class.perform_etl(use_existing=True)

        class QueryGetter:
            def __init__(self):
                self.query_handler = QueryHandler(database)
                self._src_name = EtlClass.__name__

            def search(self, query_str: str):
                resp = self.query_handler.search(query_str, incl=self._src_name)
                return resp.source_matches[self._src_name]

        return QueryGetter()

    return test_source_factory


@pytest.fixture
def mock_db_class():
    """Provide mock db class definition

    Instantiate
    """

    class NullDatabase(AbstractDatabase):
        def __init__(self, db_url: str | None = None, **db_args) -> None:  # noqa: ARG002
            self._get_all_records_values = db_args.get("get_all_records", {})
            self._added_records: dict[str, MappableConcept] = {}
            self._added_sources: dict[SourceName, MappableConcept] = {}
            self._added_merged_records: dict[str, MappableConcept] = {}
            self._updated_merge_refs: dict[str, str] = {}
            self._delete_merge_called = False
            self._delete_source_calls = set()

        def list_tables(self) -> list[str]: ...

        def drop_db(self) -> None: ...

        def check_schema_initialized(self) -> bool: ...

        def check_tables_populated(self) -> bool: ...

        def initialize_db(self) -> None: ...

        def get_source_metadata(
            self, src_name: str | SourceName
        ) -> SourceMeta | None: ...

        def get_record_by_id(
            self, concept_id: str, case_sensitive: bool = True, merge: bool = False
        ) -> dict | None: ...

        def get_refs_by_type(
            self, search_term: str, ref_type: RefType
        ) -> list[str]: ...

        def get_all_concept_ids(self, source: SourceName | None = None) -> set[str]: ...

        def get_all_records(
            self, record_type: RecordType
        ) -> Generator[dict, None, None]:
            yield from self._get_all_records_values[record_type]

        def add_source_metadata(self, source_name: SourceName, source: DataSet) -> None:
            self._added_sources[source_name] = source

        def add_record(self, disease: MappableConcept, src_name: SourceName) -> None:  # noqa: ARG002
            self._added_records[disease.id] = disease

        def add_merged_record(self, record: MappableConcept) -> None:
            self._added_merged_records[record.id] = record

        def update_merge_ref(self, concept_id: str, merge_ref: Any) -> None:  # noqa: ANN401
            self._updated_merge_refs[concept_id] = merge_ref

        def delete_normalized_concepts(self) -> None:
            self._delete_merge_called = True

        def delete_source(self, src_name: SourceName) -> None:
            self._delete_source_calls.add(src_name)

        def complete_write_transaction(self) -> None: ...

        def close_connection(self) -> None: ...

        def load_from_remote(self, url: str | None = None) -> None: ...

        def export_db(self, output_directory: Path) -> None: ...

    return NullDatabase


@pytest.fixture
def diseases() -> dict[str, MappableConcept]:
    return {
        "oncotree:ICPN": MappableConcept(
            id="oncotree:ICPN",
            name="Intracholecystic Papillary Neoplasm",
            primaryCoding=Coding(
                id="oncotree:ICPN",
                code="ICPN",
                system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
            ),
            aliases=["ICPN"],
            conceptType="Disease",
            extensions=[Extension(name="oncologic_disease", value=True)],
        ),
        "oncotree:NSCLC": MappableConcept(
            id="oncotree:NSCLC",
            name="Non-Small Cell Lung Cancer",
            conceptType="Disease",
            primaryCoding=Coding(
                id="oncotree:NSCLC",
                code="NSCLC",
                system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
            ),
            aliases=["NSCLC"],
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
            conceptType="Disease",
            primaryCoding=Coding(
                id="oncotree:NBL",
                code="NBL",
                system="https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
            ),
            aliases=["NBL"],
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
        "DOID:769": MappableConcept(
            id="DOID:769",
            conceptType="Disease",
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
            conceptType="Disease",
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
            conceptType="Disease",
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
            conceptType="Disease",
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
        "mondo:0005072": MappableConcept(
            id="mondo:0005072",
            conceptType="Disease",
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
            conceptType="Disease",
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
            conceptType="Disease",
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
            conceptType="Disease",
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
            conceptType="Disease",
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
        "MIM:309200": MappableConcept(
            id="MIM:309200",
            conceptType="Disease",
            primaryCoding=Coding(
                id="MIM:309200",
                system="https://omim.org/MIM:",
                code=code(root="309200"),
            ),
            name="MAJOR AFFECTIVE DISORDER 2",
            aliases=[
                "MAFD2",
                "MANIC-DEPRESSIVE ILLNESS",
                "MDI",
                "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
                "MDX",
                "BIPOLAR AFFECTIVE DISORDER",
                "BPAD",
            ],
        ),
        "MIM:613065": MappableConcept(
            id="MIM:613065",
            name="LEUKEMIA, ACUTE LYMPHOBLASTIC",
            conceptType="Disease",
            primaryCoding=Coding(
                id="MIM:613065",
                system="https://omim.org/MIM:",
                code=code(root="613065"),
            ),
            aliases=[
                "ALL",
                "LEUKEMIA, ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO, 1",
                "ALL1",
                "LEUKEMIA, ACUTE LYMPHOCYTIC, SUSCEPTIBILITY TO, 1",
                "LEUKEMIA, B-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
                "LEUKEMIA, T-CELL ACUTE LYMPHOBLASTIC, SUSCEPTIBILITY TO",
                "LEUKEMIA, ACUTE LYMPHOBLASTIC, B-HYPERDIPLOID, SUSCEPTIBILITY TO",
            ],
        ),
        "MIM:247640": MappableConcept(
            id="MIM:247640",
            name="LYMPHOBLASTIC LEUKEMIA, ACUTE, WITH LYMPHOMATOUS FEATURES",
            aliases=["LALL", "LYMPHOMATOUS ALL"],
            conceptType="Disease",
            primaryCoding=Coding(
                id="MIM:247640",
                system="https://omim.org/MIM:",
                code=code(root="247640"),
            ),
        ),
        "ncit:C3270": MappableConcept(
            id="ncit:C3270",
            conceptType="Disease",
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
            conceptType="Disease",
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


@pytest.fixture
def merged_diseases() -> dict[str, MappableConcept]:
    return {
        "normalize.disease.ncit:C3270": MappableConcept(
            conceptType="Disease",
            id="normalize.disease.ncit:C3270",
            primaryCoding={
                "id": "ncit:C3270",
                "code": "C3270",
                "system": "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
            },
            name="Neuroblastoma",
            mappings=[
                {
                    "coding": {
                        "id": "MONDO_0005072",
                        "code": "MONDO:0005072",
                        "system": "https://purl.obolibrary.org/obo/",
                    },
                    "relation": "exactMatch",
                },
                {
                    "coding": {
                        "id": "oncotree:NBL",
                        "code": "NBL",
                        "system": "https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
                    },
                    "relation": "exactMatch",
                },
                {
                    "coding": {
                        "id": "DOID:769",
                        "code": "DOID:769",
                        "system": "https://disease-ontology.org/?id=",
                    },
                    "relation": "exactMatch",
                },
                {
                    "coding": {
                        "id": "umls:C0027819",
                        "code": "C0027819",
                        "system": "https://www.nlm.nih.gov/research/umls/index.html",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "icdo:9500/3",
                        "code": "9500/3",
                        "system": "https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "efo:0000621",
                        "code": "0000621",
                        "system": "http://www.ebi.ac.uk/efo/EFO_",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "gard:7185",
                        "code": "7185",
                        "system": "https://rarediseases.info.nih.gov",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "mesh:D009447",
                        "code": "D009447",
                        "system": "https://meshb.nlm.nih.gov/record/ui?ui=",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "orphanet:635",
                        "code": "635",
                        "system": "https://www.orpha.net",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "umls:C2751421",
                        "code": "C2751421",
                        "system": "https://www.nlm.nih.gov/research/umls/index.html",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "medgen:18012",
                        "code": "18012",
                        "system": "https://www.ncbi.nlm.nih.gov/medgen/",
                    },
                    "relation": "relatedMatch",
                },
            ],
            aliases=[
                "NB",
                "neuroblastoma",
                "Neural Crest Tumor, Malignant",
                "Neuroblastoma (Schwannian Stroma-poor)",
                "neuroblastoma (Schwannian Stroma-poor)",
                "Neuroblastoma (Schwannian Stroma-Poor)",
                "Neuroblastoma, NOS",
                "NEUROBLASTOMA, MALIGNANT",
                "Neuroblastoma (NBL)",
                "neural Crest tumor, malignant",
                "neuroblastoma, malignant",
            ],
            extensions=[
                Extension(name="oncologic_disease", value=True),
            ],
        ),
        "normalize.disease.ncit:C167370": MappableConcept(
            conceptType="Disease",
            id="normalize.disease.ncit:C167370",
            primaryCoding={
                "id": "ncit:C167370",
                "code": "C167370",
                "system": "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
            },
            name="Skin Myoepithelioma",
            aliases=["Cutaneous Myoepithelioma"],
        ),
        "normalize.disease.ncit:C9012": MappableConcept(
            id="normalize.disease.ncit:C9012",
            primaryCoding=Coding(
                id="ncit:C9012",
                code="C9012",
                system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
            ),
            conceptType="Disease",
            name="Adult Cystic Teratoma",
            mappings=[
                ConceptMapping(
                    relation=Relation.EXACT_MATCH,
                    coding=Coding(
                        id="MONDO_0004099",
                        code=code(root="MONDO:0004099"),
                        system="https://purl.obolibrary.org/obo/",
                    ),
                ),
                ConceptMapping(
                    relation=Relation.EXACT_MATCH,
                    coding=Coding(
                        id="DOID:7079",
                        code=code(root="7079"),
                        system="https://disease-ontology.org/?id=",
                    ),
                ),
                ConceptMapping(
                    relation=Relation.RELATED_MATCH,
                    coding=Coding(
                        id="icdo:9080/0",
                        system="https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
                        code=code(root="9080/0"),
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
            aliases=[
                "Adult cystic teratoma",
                "cystic teratoma of adults",
                "adult cystic teratoma",
            ],
            extensions=[Extension(name="oncologic_disease", value=True)],
        ),
        "normalize.disease.mondo:0010648": MappableConcept(
            conceptType="Disease",
            id="normalize.disease.mondo:0010648",
            primaryCoding={
                "id": "MONDO_0010648",
                "code": "MONDO:0010648",
                "system": "https://purl.obolibrary.org/obo/",
            },
            name="major affective disorder 2",
            mappings=[
                {
                    "coding": {
                        "id": "MIM:309200",
                        "code": "309200",
                        "system": "https://omim.org/MIM:",
                    },
                    "relation": "exactMatch",
                },
                {
                    "coding": {
                        "id": "mesh:C564108",
                        "code": "C564108",
                        "system": "https://meshb.nlm.nih.gov/record/ui?ui=",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "medgen:326975",
                        "code": "326975",
                        "system": "https://www.ncbi.nlm.nih.gov/medgen/",
                    },
                    "relation": "relatedMatch",
                },
                {
                    "coding": {
                        "id": "umls:C1839839",
                        "code": "C1839839",
                        "system": "https://www.nlm.nih.gov/research/umls/index.html",
                    },
                    "relation": "relatedMatch",
                },
            ],
            aliases=[
                "MAFD2",
                "MDI",
                "MDX",
                "MANIC-DEPRESSIVE ILLNESS",
                "BPAD",
                "MAFD2",
                "BIPOLAR AFFECTIVE DISORDER",
                "MANIC-DEPRESSIVE PSYCHOSIS, X-LINKED",
                "major affective disorder 2, X-linked dominant",
                "MAJOR affective disorder 2",
                "bipolar affective disorder",
                "major affective disorder 2",
                "manic-depressive illness",
                "manic-depressive psychosis, X-linked",
            ],
        ),
        "normalize.disease.ncit:C8091": MappableConcept(
            id="ncit:C8091",
            conceptType="Disease",
            primaryCoding=Coding(
                id="ncit:C8091",
                system="https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                code=code(root="C8091"),
            ),
            mappings=[
                ConceptMapping(
                    relation=Relation.EXACT_MATCH,
                    coding=Coding(
                        id="MONDO_0003587",
                        code=code(root="MONDO:0003587"),
                        system="https://purl.obolibrary.org/obo/",
                    ),
                ),
                ConceptMapping(
                    relation=Relation.EXACT_MATCH,
                    coding=Coding(
                        id="DOID:5695",
                        code=code(root="5696"),
                        system="https://disease-ontology.org/?id=",
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
            name="Childhood Liposarcoma",
            aliases=[
                "liposarcoma",
                "Liposarcoma",
                "Pediatric Liposarcoma",
                "childhood liposarcoma",
                "pediatric liposarcoma",
            ],
            extensions=[
                Extension(name="pediatric_disease", value=True),
                Extension(name="oncologic_disease", value=True),
            ],
        ),
    }


@pytest.fixture
def datasets() -> dict[str, DataSet]:
    return {
        SourceName.ONCOTREE: DataSet(
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
        ),
        SourceName.DO: DataSet(
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
        ),
        SourceName.MONDO: DataSet(
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
        ),
        SourceName.OMIM: DataSet(
            name="OMIM",
            version="20240806",
            license=MappableConcept(
                name="custom",
                primaryCoding=Coding(
                    code=code(root="OMIM-use-agreement"),
                    system="https://omim.org",
                    iris=[iriReference(root="https://omim.org/help/agreement")],
                ),
                extensions=[
                    Extension(
                        name="license_attributes",
                        value={
                            "non_commercial": False,
                            "share_alike": True,
                            "attribution": True,
                        },
                    ),
                ],
            ),
            extensions=[
                Extension(
                    name="data_url",
                    value="https://www.omim.org/downloads",
                ),
                Extension(name="rdp_url", value="http://reusabledata.org/omim.html"),
            ],
        ),
        SourceName.NCIT: DataSet(
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
                Extension(
                    name="data_url", value="https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/"
                ),
                Extension(name="rdp_url", value="http://reusabledata.org/ncit.html"),
            ],
        ),
    }
