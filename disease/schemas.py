"""This module contains data models for representing VICC normalized
disease records.
"""
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictStr,
    constr,
    field_validator,
)

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
                "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                "version": "21.01d",
                "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                "rdp_url": "http://reusabledata.org/ncit.html",
                "data_license_attributes": {
                    "non_commercial": False,
                    "attribution": True,
                    "share_alike": False,
                },
            }
        }
    )


class MatchesKeyed(BaseModel):
    """Container for matching information from an individual source.
    Used when matches are requested as an object, not an array.
    """

    match_type: MatchType
    records: List[Disease] = []
    source_meta_: SourceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "match_type": 80,
                "records": [
                    {
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
                ],
                "source_meta_": {
                    "data_license": "CC BY 4.0",
                    "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                    "version": "21.01d",
                    "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                    "rdp_url": "http://reusabledata.org/ncit.html",
                    "data_license_attributes": {
                        "non_commercial": False,
                        "attribution": True,
                        "share_alike": False,
                    },
                },
            }
        }
    )


class MatchesListed(BaseModel):
    """Container for matching information from an individual source.
    Used when matches are requested as an array, not an object.
    """

    source: SourceName
    match_type: MatchType
    records: List[Disease] = []
    source_meta_: SourceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "NCIt",
                "match_type": 80,
                "records": [
                    {
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
                ],
                "source_meta_": {
                    "data_license": "CC BY 4.0",
                    "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                    "version": "21.01d",
                    "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                    "rdp_url": "http://reusabledata.org/ncit.html",
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


CURIE = constr(pattern=r"^\w[^:]*:.+$")


class Extension(BaseModel):
    """The Extension class provides VODs with a means to extend descriptions with other
    attributes unique to a content provider.
    """

    type: Literal["Extension"] = "Extension"
    name: StrictStr
    value: Optional[Any] = None


class DiseaseValueObject(BaseModel, extra="forbid"):
    """A reference to a Disease as defined by an authority. For human diseases, the
    use of `MONDO <https://registry.identifiers.org/registry/mondo>` as the disease
    authority is RECOMMENDED.
    """

    id: CURIE
    type: Literal["Disease"] = "Disease"


class DiseaseDescriptor(BaseModel, extra="forbid"):
    """This descriptor class is used for describing Disease domain entities."""

    id: Optional[StrictStr] = None
    type: Literal["DiseaseDescriptor"] = "DiseaseDescriptor"
    disease: Union[CURIE, DiseaseValueObject]
    label: Optional[StrictStr] = None
    description: Optional[StrictStr] = None
    xrefs: List[CURIE] = []
    alternate_labels: List[StrictStr] = []
    extensions: List[Extension] = []

    @field_validator("xrefs")
    def check_count_value(cls, v):
        """Check xrefs value"""
        if v:
            assert len(v) == len(
                {xref for xref in v}
            ), "xrefs must contain unique items"
        return v


class NormalizationService(BaseModel):
    """Response containing one or more merged records and source data."""

    query: StrictStr
    warnings: Optional[Dict] = None
    match_type: MatchType
    disease_descriptor: Optional[DiseaseDescriptor] = None
    source_meta_: Optional[Dict[SourceName, SourceMeta]] = None
    service_meta_: ServiceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "childhood leukemia",
                "warnings": None,
                "match_type": 80,
                "disease_descriptor": {
                    "id": "normalize:childhood%20leukemia",
                    "type": "DiseaseDescriptor",
                    "disease": "ncit:C4989",
                    "label": "Childhood Leukemia",
                    "xrefs": ["mondo:0004355", "DOID:7757"],
                    "alternate_labels": [
                        "childhood leukemia (disease)",
                        "leukemia",
                        "pediatric leukemia (disease)",
                        "Leukemia",
                        "leukemia (disease) of childhood",
                    ],
                    "extensions": [
                        {
                            "type": "Extension",
                            "name": "pediatric_disease",
                            "value": True,
                        },
                        {
                            "type": "Extension",
                            "name": "associated_with",
                            "value": ["umls:C1332977"],
                        },
                    ],
                },
                "source_meta_": {
                    "NCIt": {
                        "data_license": "CC BY 4.0",
                        "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                        "version": "21.01d",
                        "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                        "rdp_url": "http://reusabledata.org/ncit.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": False,
                        },
                    },
                    "Mondo": {
                        "data_license": "CC BY 4.0",
                        "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                        "version": "20210129",
                        "data_url": "https://mondo.monarchinitiative.org/pages/download/",  # noqa: E501
                        "rdp_url": "http://reusabledata.org/monarch.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": False,
                        },
                    },
                    "DO": {
                        "data_license": "CC0 1.0",
                        "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",  # noqa: E501
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
    source_matches: Union[Dict[SourceName, MatchesKeyed], List[MatchesListed]]
    service_meta_: ServiceMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Von Hippel-Lindau Syndrome",
                "warnings": None,
                "source_matches": [
                    {
                        "source": "NCIt",
                        "match_type": 80,
                        "records": [
                            {
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
                        ],
                        "source_meta_": {
                            "data_license": "CC BY 4.0",
                            "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                            "version": "21.01d",
                            "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                            "rdp_url": "http://reusabledata.org/ncit.html",
                            "data_license_attributes": {
                                "non_commercial": False,
                                "attribution": True,
                                "share_alike": False,
                            },
                        },
                    }
                ],
                "service_meta_": {
                    "name": "disease-normalizer",
                    "version": __version__,
                    "response_datetime": "2021-04-05T16:44:15.367831",
                    "url": "https://github.com/cancervariants/disease-normalization",  # noqa: E501
                },
            }
        }
    )
