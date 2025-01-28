"""Contains data models for representing VICC normalized disease records."""

import datetime
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Literal

from ga4gh.core.models import (
    Coding,
    ConceptMapping,
    MappableConcept,
    Relation,
    code,
)
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr

from disease import __version__


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    LABEL = 80
    ALIAS = 60
    XREF = 60
    ASSOCIATED_WITH = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(str, Enum):
    """Define string constraints to ensure consistent capitalization."""

    NCIT = "NCIt"
    MONDO = "Mondo"
    DO = "DO"
    ONCOTREE = "OncoTree"
    OMIM = "OMIM"


class SourceIDAfterNamespace(Enum):
    """Define string constraints after namespace."""

    NCIT = "C"
    MONDO = ""
    DO = ""  # noqa: PIE796
    ONCOTREE = ""  # noqa: PIE796
    OMIM = ""  # noqa: PIE796


class NamespacePrefix(Enum):
    """Define string constraints for how concept ID namespace prefixes are
    stored.
    """

    # built-in sources
    NCIT = "ncit"
    MONDO = "mondo"
    DOID = "DOID"
    DO = DOID
    OMIM = "MIM"
    ONCOTREE = "oncotree"
    # external sources
    EFO = "efo"
    GARD = "gard"
    ICD9CM = "icd9.cm"
    ICD10 = "icd10"
    ICD10WHO = ICD10
    ICD10CM = "icd10.cm"
    ICDO = "icdo"
    IMDRF = "imdrf"
    KEGG = "kegg.disease"
    MEDDRA = "meddra"
    MEDGEN = "medgen"
    MESH = "mesh"
    ORPHANET = "orphanet"
    UMLS = "umls"


# Source to URI. Will use  system URI prefix, OBO Foundry persistent URL (PURL), or source homepage
NAMESPACE_TO_SYSTEM_URI: MappingProxyType[NamespacePrefix, str] = MappingProxyType(
    {
        NamespacePrefix.NCIT: "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
        NamespacePrefix.MONDO: "https://purl.obolibrary.org/obo/",
        NamespacePrefix.DO: "https://disease-ontology.org/?id=",
        NamespacePrefix.DOID: "https://disease-ontology.org/?id=",
        NamespacePrefix.OMIM: "https://omim.org/MIM:",
        NamespacePrefix.ONCOTREE: "https://oncotree.mskcc.org/?version=oncotree_latest_stable&field=CODE&search=",
        NamespacePrefix.EFO: "http://www.ebi.ac.uk/efo/EFO_",
        NamespacePrefix.GARD: "https://rarediseases.info.nih.gov",
        NamespacePrefix.ICD9CM: "https://archive.cdc.gov/www_cdc_gov/nchs/icd/icd9cm.htm",
        NamespacePrefix.ICD10: "https://icd.who.int/browse10/2016/en#/",
        NamespacePrefix.ICD10CM: "https://www.cdc.gov/nchs/icd/icd-10-cm/index.html",
        NamespacePrefix.ICD10WHO: "https://icd.who.int/browse10/2016/en#/",
        NamespacePrefix.ICDO: "https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
        NamespacePrefix.IMDRF: "https://www.imdrf.org/",
        NamespacePrefix.KEGG: "https://www.genome.jp/kegg/disease/",
        NamespacePrefix.MEDDRA: "https://bioportal.bioontology.org/ontologies/MEDDRA?p=classes&conceptid=",
        NamespacePrefix.MEDGEN: "https://www.ncbi.nlm.nih.gov/medgen/",
        NamespacePrefix.MESH: "https://meshb.nlm.nih.gov/record/ui?ui=",
        NamespacePrefix.ORPHANET: "https://www.orpha.net",
        NamespacePrefix.UMLS: "https://www.nlm.nih.gov/research/umls/index.html",
    }
)


def get_concept_mapping(
    concept_id: str, relation: Relation = Relation.RELATED_MATCH
) -> ConceptMapping:
    """Get concept mapping for CURIE identifier

    ``system`` will use system prefix URL, OBO Foundry persistent URL (PURL), or
    source homepage, in that order of preference.

    :param concept_id: Concept identifier represented as a curie
    :param relation: SKOS mapping relationship, default is relatedMatch
    :raises ValueError: If source of concept ID is not a valid ``NamespacePrefix``
    :return: Concept mapping for identifier
    """
    source, source_code = concept_id.split(":")

    try:
        source = NamespacePrefix(source)
    except ValueError:
        try:
            source = NamespacePrefix(source.upper())
        except ValueError as e:
            err_msg = f"Namespace prefix not supported: {source}"
            raise ValueError(err_msg) from e

    id_ = concept_id

    if source == NamespacePrefix.MONDO:
        source_code = concept_id.upper()
        id_ = source_code.replace(":", "_")
    elif source == NamespacePrefix.DOID:
        source_code = concept_id

    return ConceptMapping(
        coding=Coding(
            id=id_,
            code=code(source_code),
            system=NAMESPACE_TO_SYSTEM_URI[source],
        ),
        relation=relation,
    )


class SourcePriority(IntEnum):
    """Define priorities for sources in building merged concepts."""

    NCIT = 1
    MONDO = 2
    OMIM = 3
    ONCOTREE = 4
    DO = 5


class Disease(BaseModel):
    """Define disease record."""

    label: StrictStr
    concept_id: StrictStr
    aliases: list[StrictStr] = []
    xrefs: list[StrictStr] = []
    associated_with: list[StrictStr] = []
    pediatric_disease: bool | None = None
    oncologic_disease: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "label": "Von Hippel-Lindau Syndrome",
                "concept_id": "ncit:C3105",
                "aliases": [
                    "Von Hippel-Lindau Syndrome (VHL)",
                    "Von Hippel-Lindau Disease",
                    "Cerebroretinal Angiomatosis",
                    "von Hippel-Lindau syndrome",
                    "VHL syndrome",
                ],
                "xrefs": [],
                "associated_with": ["umls:C0019562"],
                "pediatric_disease": None,
                "oncologic_disease": None,
            }
        }
    )


class RecordType(str, Enum):
    """Record item types."""

    IDENTITY = "identity"
    MERGER = "merger"


class RefType(str, Enum):
    """Reference item types."""

    # Must be in descending MatchType order.
    LABEL = "label"
    ALIASES = "alias"
    XREFS = "xref"
    ASSOCIATED_WITH = "associated_with"


class DataLicenseAttributes(BaseModel):
    """Define constraints for data license attributes."""

    non_commercial: StrictBool
    share_alike: StrictBool
    attribution: StrictBool


class SourceMeta(BaseModel):
    """Metadata for a given source to return in response object."""

    data_license: StrictStr
    data_license_url: StrictStr
    version: StrictStr
    data_url: StrictStr | None = None
    rdp_url: StrictStr | None = None
    data_license_attributes: DataLicenseAttributes

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_license": "CC BY 4.0",
                "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",
                "version": "21.01d",
                "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",
                "rdp_url": "http://reusabledata.org/ncit.html",
                "data_license_attributes": {
                    "non_commercial": False,
                    "attribution": True,
                    "share_alike": False,
                },
            }
        }
    )


class SourceSearchMatches(BaseModel):
    """Container for matching information from an individual source."""

    match_type: MatchType
    records: list[Disease] = []
    source_meta_: SourceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "match_type": 80,
                "records": [
                    {
                        "label": "non-small cell lung carcinoma",
                        "concept_id": "mondo:0005233",
                        "aliases": [
                            "non-small cell lung carcinoma (disease)",
                            "non-small cell carcinoma of lung",
                            "non-small cell lung cancer",
                            "non-small cell cancer of lung",
                            "non-small cell carcinoma of the lung",
                            "non-small cell cancer of the lung",
                            "NSCLC",
                            "NSCLC - non-small cell lung cancer",
                        ],
                        "xrefs": ["DOID:3908", "ncit:C2926", "oncotree:NSCLC"],
                        "associated_with": [
                            "mesh:D002289",
                            "efo:0003060",
                            "umls:C0007131",
                        ],
                    }
                ],
                "source_meta_": {
                    "data_license": "CC BY 4.0",
                    "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",
                    "version": "2023-07-03",
                    "data_url": "https://mondo.monarchinitiative.org/pages/download/",
                    "rdp_url": "http://reusabledata.org/monarch.html",
                    "data_license_attributes": {
                        "non_commercial": False,
                        "attribution": True,
                        "share_alike": False,
                    },
                },
            }
        }
    )


class ServiceMeta(BaseModel):
    """Metadata regarding the disease-normalization service."""

    name: Literal["disease-normalizer"] = "disease-normalizer"
    version: StrictStr
    response_datetime: datetime.datetime
    url: Literal["https://github.com/cancervariants/disease-normalization"] = (
        "https://github.com/cancervariants/disease-normalization"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "disease-normalizer",
                "version": __version__,
                "response_datetime": "2021-04-05T16:44:15.367831",
                "url": "https://github.com/cancervariants/disease-normalization",
            }
        }
    )


class NormalizationService(BaseModel):
    """Response containing one or more merged records and source data."""

    query: StrictStr
    warnings: dict | None = None
    match_type: MatchType
    disease: MappableConcept | None = None
    source_meta_: dict[SourceName, SourceMeta] | None = None
    service_meta_: ServiceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "childhood leukemia",
                "warnings": None,
                "match_type": 80,
                "disease": {
                    "id": "normalize.disease.ncit:C4989",
                    "primaryCode": "ncit:C4989",
                    "conceptType": "Disease",
                    "label": "Childhood Leukemia",
                    "mappings": [
                        {
                            "coding": {
                                "id": "ncit:C4989",
                                "code": "C4989",
                                "system": "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                            },
                            "relation": "exactMatch",
                        },
                        {
                            "coding": {
                                "id": "MONDO_0004355",
                                "code": "MONDO:0004355",
                                "system": "https://purl.obolibrary.org/obo/",
                            },
                            "relation": "exactMatch",
                        },
                        {
                            "coding": {
                                "id": "DOID:7757",
                                "code": "DOID:7757",
                                "system": "https://disease-ontology.org/?id=",
                            },
                            "relation": "exactMatch",
                        },
                        {
                            "coding": {
                                "id": "umls:C1332977",
                                "code": "C1332977",
                                "system": "https://www.nlm.nih.gov/research/umls/index.html",
                            },
                            "relation": "relatedMatch",
                        },
                    ],
                    "extensions": [
                        {
                            "name": "aliases",
                            "value": [
                                "childhood leukemia (disease)",
                                "leukemia",
                                "pediatric leukemia (disease)",
                                "Leukemia",
                                "leukemia (disease) of childhood",
                            ],
                        },
                        {
                            "name": "pediatric_disease",
                            "value": True,
                        },
                    ],
                },
                "source_meta_": {
                    "NCIt": {
                        "data_license": "CC BY 4.0",
                        "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",
                        "version": "21.01d",
                        "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",
                        "rdp_url": "http://reusabledata.org/ncit.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": False,
                        },
                    },
                    "Mondo": {
                        "data_license": "CC BY 4.0",
                        "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",
                        "version": "20210129",
                        "data_url": "https://mondo.monarchinitiative.org/pages/download/",
                        "rdp_url": "http://reusabledata.org/monarch.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": False,
                        },
                    },
                    "DO": {
                        "data_license": "CC0 1.0",
                        "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                        "version": "20210305",
                        "data_url": "http://www.obofoundry.org/ontology/doid.html",
                        "rdp_url": None,
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": False,
                            "share_alike": False,
                        },
                    },
                },
                "service_meta_": {
                    "name": "disease-normalizer",
                    "version": __version__,
                    "response_datetime": "2021-04-05T16:44:15.367831",
                    "url": "https://github.com/cancervariants/disease-normalization",
                },
            }
        }
    )


class SearchService(BaseModel):
    """Core response schema containing matches for each source"""

    query: StrictStr
    warnings: dict | None = None
    source_matches: dict[SourceName, SourceSearchMatches]
    service_meta_: ServiceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "query": "nsclc",
            "source_matches": {
                "OMIM": {
                    "records": [],
                    "source_meta_": {
                        "data_license": "custom",
                        "data_license_url": "https://omim.org/help/agreement",
                        "version": "20231030",
                        "data_url": "https://www.omim.org/downloads",
                        "rdp_url": "http://reusabledata.org/omim.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": True,
                        },
                    },
                },
                "DO": {
                    "records": [
                        {
                            "label": "lung non-small cell carcinoma",
                            "concept_id": "DOID:3908",
                            "aliases": [
                                "Non-small cell lung cancer",
                                "NSCLC",
                                "non-small cell lung carcinoma",
                            ],
                            "xrefs": ["ncit:C2926"],
                            "associated_with": [
                                "mesh:D002289",
                                "kegg.disease:05223",
                                "efo:0003060",
                                "umls:C0007131",
                            ],
                            "match_type": 60,
                        }
                    ],
                    "source_meta_": {
                        "data_license": "CC0 1.0",
                        "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                        "version": "2023-07-24",
                        "data_url": "http://www.obofoundry.org/ontology/doid.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": False,
                            "share_alike": False,
                        },
                    },
                },
            },
            "service_meta_": {
                "name": "disease-normalizer",
                "version": "0.4.0.dev1",
                "response_datetime": "2023-10-31T10:53:30.890262",
                "url": "https://github.com/cancervariants/disease-normalization",
            },
        }
    )
