"""Contains data models for representing VICC normalized disease records."""

import datetime
from enum import Enum, IntEnum
from typing import Literal

from ga4gh.core.models import MappableConcept
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
    COHD = "cohd"
    DECIPHER = "decipher"
    EFO = "efo"
    GARD = "gard"
    HP = "HP"
    HPO = HP
    ICD9 = "icd9"
    ICD9CM = "icd9.cm"
    ICD10 = "icd10"
    ICD10WHO = ICD10
    ICD10CM = "icd10.cm"
    ICD11 = "icd11"
    ICDO = "icdo"
    IDO = "ido"
    IMDRF = "imdrf"
    KEGG = "kegg.disease"
    MEDDRA = "meddra"
    MEDGEN = "medgen"
    MESH = "mesh"
    MF = "mf"
    MP = "MP"
    MPATH = "mpath"
    NIFSTD = "nifstd"
    OBI = "obi"
    OGMS = "ogms"
    ORPHANET = "orphanet"
    PATO = "pato"
    SCDO = "scdo"
    UMLS = "umls"
    WIKIPEDIA = "wikipedia.en"
    WIKIDATA = "wikidata"


# Source to URI. Will use OBO Foundry persistent URL (PURL) or source homepage
NAMESPACE_TO_SYSTEM_URI: dict[NamespacePrefix, str] = {
    NamespacePrefix.NCIT: "http://purl.obolibrary.org/obo/ncit.owl",
    NamespacePrefix.MONDO: "http://purl.obolibrary.org/obo/mondo.owl",
    NamespacePrefix.DO: "http://purl.obolibrary.org/obo/doid.owl",
    NamespacePrefix.DOID: "http://purl.obolibrary.org/obo/doid.owl",
    NamespacePrefix.OMIM: "https://www.omim.org",
    NamespacePrefix.ONCOTREE: "https://oncotree.mskcc.org",
    NamespacePrefix.COHD: "https://cohd.io",
    NamespacePrefix.DECIPHER: "https://www.deciphergenomics.org",
    NamespacePrefix.EFO: "https://www.ebi.ac.uk/efo/",
    NamespacePrefix.GARD: "https://rarediseases.info.nih.gov",
    NamespacePrefix.HP: "http://purl.obolibrary.org/obo/hp.owl",
    NamespacePrefix.HPO: "http://purl.obolibrary.org/obo/hp.owl",
    NamespacePrefix.ICD11: "https://icd.who.int/en/",
    NamespacePrefix.ICDO: "https://www.who.int/standards/classifications/other-classifications/international-classification-of-diseases-for-oncology/",
    NamespacePrefix.KEGG: "https://www.genome.jp/kegg/disease/",
    NamespacePrefix.MEDDRA: "https://www.meddra.org",
    NamespacePrefix.MEDGEN: "https://www.ncbi.nlm.nih.gov/medgen/",
    NamespacePrefix.MESH: "https://id.nlm.nih.gov/mesh/",
    NamespacePrefix.MP: "http://purl.obolibrary.org/obo/mp.owl",
    NamespacePrefix.OBI: "http://purl.obolibrary.org/obo/obi.owl",
    NamespacePrefix.ORPHANET: "https://www.orpha.net",
    NamespacePrefix.PATO: "http://purl.obolibrary.org/obo/pato.owl",
    NamespacePrefix.UMLS: "https://www.nlm.nih.gov/research/umls/index.html",
    NamespacePrefix.WIKIPEDIA: "https://en.wikipedia.org",
    NamespacePrefix.WIKIDATA: "https://www.wikidata.org",
}

# URI to source
SYSTEM_URI_TO_NAMESPACE = {
    system_uri: ns.value for ns, system_uri in NAMESPACE_TO_SYSTEM_URI.items()
}


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
                                "code": "ncit:C4989",
                                "system": "https://www.ebi.ac.uk/ols4/ontologies/ncit/classes?short_form=NCIT_",
                            },
                            "relation": "exactMatch",
                        },
                        {
                            "coding": {
                                "code": "mondo:0004355",
                                "system": "http://purl.obolibrary.org/obo/mondo.owl",
                            },
                            "relation": "relatedMatch",
                        },
                        {
                            "coding": {
                                "code": "DOID:7757",
                                "system": "http://purl.obolibrary.org/obo/doid.owl",
                            },
                            "relation": "relatedMatch",
                        },
                        {
                            "coding": {
                                "code": "umls:C1332977",
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
