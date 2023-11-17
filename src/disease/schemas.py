"""Contains data models for representing VICC normalized disease records."""
from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Literal, Optional

from ga4gh.core import core_models
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr

from disease.version import __version__


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
    DO = ""
    ONCOTREE = ""
    OMIM = ""


class NamespacePrefix(Enum):
    """Define string constraints for how concept ID namespace prefixes are
    stored.
    """

    # built-in sources
    NCIT = "ncit"
    MONDO = "mondo"
    DO = "DOID"
    OMIM = "omim"
    ONCOTREE = "oncotree"
    # external sources
    COHD = "cohd"
    DECIPHER = "decipher"
    EFO = "efo"
    GARD = "gard"
    HPO = "HP"
    ICD9 = "icd9"
    ICD9CM = "icd9.cm"
    ICD10 = "icd10"
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
    OMIMPS = "omimps"
    ORPHANET = "orphanet"
    PATO = "pato"
    SCDO = "scdo"
    UMLS = "umls"
    WIKIPEDIA = "wikipedia.en"
    WIKIDATA = "wikidata"


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
    aliases: List[StrictStr] = []
    xrefs: List[StrictStr] = []
    associated_with: List[StrictStr] = []
    pediatric_disease: Optional[bool] = None

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
            }
        }
    )


class DataLicenseAttributes(BaseModel):
    """Define constraints for data license attributes."""

    non_commercial: StrictBool
    share_alike: StrictBool
    attribution: StrictBool


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


class SourceMeta(BaseModel):
    """Metadata for a given source to return in response object."""

    data_license: StrictStr
    data_license_url: StrictStr
    version: StrictStr
    data_url: Optional[StrictStr] = None
    rdp_url: Optional[StrictStr] = None
    data_license_attributes: Dict[StrictStr, StrictBool]

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
    records: List[Disease] = []
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
    response_datetime: datetime
    url: Literal[
        "https://github.com/cancervariants/disease-normalization"
    ] = "https://github.com/cancervariants/disease-normalization"

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
    warnings: Optional[Dict] = None
    match_type: MatchType
    normalized_id: Optional[str] = None
    disease: Optional[core_models.Disease] = None
    source_meta_: Optional[Dict[SourceName, SourceMeta]] = None
    service_meta_: ServiceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "childhood leukemia",
                "warnings": None,
                "match_type": 80,
                "normalized_id": "ncit:C4989",
                "disease": {
                    "id": "normalize.disease.ncit:C4989",
                    "type": "Disease",
                    "label": "Childhood Leukemia",
                    "aliases": [
                        "childhood leukemia (disease)",
                        "leukemia",
                        "pediatric leukemia (disease)",
                        "Leukemia",
                        "leukemia (disease) of childhood",
                    ],
                    "mappings": [
                        {
                            "coding": {"code": "0004355", "system": "mondo"},
                            "relation": "relatedMatch",
                        },
                        {
                            "coding": {"code": "7757", "system": "doid"},
                            "relation": "relatedMatch",
                        },
                        {
                            "coding": {"code": "C1332977", "system": "umls"},
                            "relation": "relatedMatch",
                        },
                    ],
                    "extensions": [
                        {
                            "type": "Extension",
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
    warnings: Optional[Dict] = None
    source_matches: Dict[SourceName, SourceSearchMatches]
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
