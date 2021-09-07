"""This module contains data models for representing VICC normalized
disease records.
"""
from typing import Any, Dict, Type, List, Optional, Union
from enum import Enum, IntEnum
from pydantic import BaseModel, StrictBool
from datetime import datetime
from ga4gh.vrsatile.pydantic.vrsatile_model import ValueObjectDescriptor


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    LABEL = 80
    ALIAS = 60
    XREF = 60
    ASSOCIATED_WITH = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(Enum):
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
    EFO = "efo"
    GARD = "gard"
    HPO = "HP"
    ICD9 = "icd9"
    ICD9CM = "icd9.cm"
    ICD10 = "icd10"
    ICD10CM = "icd10.cm"
    ICDO = "icdo"
    IDO = "ido"
    IMDRF = "imdrf"
    KEGG = "kegg.disease"
    MEDDRA = "meddra"
    MEDGEN = "medgen"
    MESH = "mesh"
    MF = "mf"
    MP = "MP"
    NIFSTD = "nifstd"
    OGMS = "ogms"
    OMIMPS = "omimps"
    ORPHANET = "orphanet"
    PATO = "pato"
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

    label: str
    concept_id: str
    aliases: Optional[List[str]] = []
    xrefs: Optional[List[str]] = []
    associated_with: Optional[List[str]] = []
    pediatric_disease: Optional[bool]

    class Config:
        """Configure model."""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['Disease']) -> None:
            """Configure OpenAPI schema."""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "label": "Von Hippel-Lindau Syndrome",
                "concept_id": "ncit:C3105",
                "aliases": [
                    "Von Hippel-Lindau Syndrome (VHL)",
                    "Von Hippel-Lindau Disease",
                    "Cerebroretinal Angiomatosis",
                    "von Hippel-Lindau syndrome",
                    "VHL syndrome"
                ],
                "xrefs": [],
                "associated_with": ["umls:C0019562"],
                "pediatric_disease": None,
            }


class DataLicenseAttributes(BaseModel):
    """Define constraints for data license attributes."""

    non_commercial: StrictBool
    share_alike: StrictBool
    attribution: StrictBool


class ItemTypes(str, Enum):
    """Item types used in DynamoDB."""

    # Must be in descending MatchType order.
    LABEL = 'label'
    ALIASES = 'alias'
    XREFS = 'xref'
    ASSOCIATED_WITH = 'associated_with'


class SourceMeta(BaseModel):
    """Metadata for a given source to return in response object."""

    data_license: str
    data_license_url: str
    version: str
    data_url: Optional[str]
    rdp_url: Optional[str]
    data_license_attributes: Dict[str, StrictBool]

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['SourceMeta']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "data_license": "CC BY 4.0",
                "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                "version": "21.01d",
                "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                "rdp_url": "http://reusabledata.org/ncit.html",
                "data_license_attributes": {
                    "non_commercial": False,
                    "attribution": True,
                    "share_alike": False
                }
            }


class MatchesKeyed(BaseModel):
    """Container for matching information from an individual source.
    Used when matches are requested as an object, not an array.
    """

    match_type: MatchType
    records: List[Disease]
    source_meta_: SourceMeta

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['MatchesKeyed']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "match_type": 80,
                "records": [{
                    "label": "Von Hippel-Lindau Syndrome",
                    "concept_id": "ncit:C3105",
                    "aliases": [
                        "Von Hippel-Lindau Syndrome (VHL)",
                        "Von Hippel-Lindau Disease",
                        "Cerebroretinal Angiomatosis",
                        "von Hippel-Lindau syndrome",
                        "VHL syndrome"
                    ],
                    "xrefs": [],
                    "associated_with": ["umls:C0019562"],
                    "pediatric_disease": None,
                }],
                "source_meta_": {
                    "data_license": "CC BY 4.0",
                    "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                    "version": "21.01d",
                    "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                    "rdp_url": "http://reusabledata.org/ncit.html",
                    "data_license_attributes": {
                        "non_commercial": False,
                        "attribution": True,
                        "share_alike": False
                    }
                }
            }


class MatchesListed(BaseModel):
    """Container for matching information from an individual source.
    Used when matches are requested as an array, not an object.
    """

    source: SourceName
    match_type: MatchType
    records: List[Disease]
    source_meta_: SourceMeta

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['MatchesListed']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "source": "NCIt",
                "match_type": 80,
                "records": [{
                    "label": "Von Hippel-Lindau Syndrome",
                    "concept_id": "ncit:C3105",
                    "aliases": [
                        "Von Hippel-Lindau Syndrome (VHL)",
                        "Von Hippel-Lindau Disease",
                        "Cerebroretinal Angiomatosis",
                        "von Hippel-Lindau syndrome",
                        "VHL syndrome"
                    ],
                    "xrefs": [],
                    "associated_with": ["umls:C0019562"],
                    "pediatric_disease": None
                }],
                "source_meta_": {
                    "data_license": "CC BY 4.0",
                    "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                    "version": "21.01d",
                    "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                    "rdp_url": "http://reusabledata.org/ncit.html",
                    "data_license_attributes": {
                        "non_commercial": False,
                        "attribution": True,
                        "share_alike": False
                    }
                }
            }


class ServiceMeta(BaseModel):
    """Metadata regarding the disease-normalization service."""

    name = 'disease-normalizer'
    version: str
    response_datetime: datetime
    url = 'https://github.com/cancervariants/disease-normalization'

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['ServiceMeta']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                'name': 'disease-normalizer',
                'version': '0.1.0',
                'response_datetime': '2021-04-05T16:44:15.367831',
                'url': 'https://github.com/cancervariants/disease-normalization'  # noqa: E501
            }


class NormalizationService(BaseModel):
    """Response containing one or more merged records and source data."""

    query: str
    warnings: Optional[Dict]
    match_type: MatchType
    value_object_descriptor: Optional[ValueObjectDescriptor]
    source_meta_: Optional[Dict[SourceName, SourceMeta]]
    service_meta_: ServiceMeta

    class Config:
        """Configure model."""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['NormalizationService']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "query": "childhood leukemia",
                "warnings": None,
                "match_type": 80,
                "disease_descriptor": {
                    "id": "normalize:childhood%20leukemia",
                    "type": "DiseaseDescriptor",
                    "disease_id": "ncit:C4989",
                    "label": "Childhood Leukemia",
                    "xrefs": [
                        "mondo:0004355",
                        "DOID:7757"
                    ],
                    "alternate_labels": [
                        "childhood leukemia (disease)",
                        "leukemia",
                        "pediatric leukemia (disease)",
                        "Leukemia",
                        "leukemia (disease) of childhood"
                    ],
                    "extensions": [
                        {
                            "type": "Extension",
                            "name": "pediatric_disease",
                            "value": True
                        },
                        {
                            "type": "Extension",
                            "name": "associated_with",
                            "value": ["umls:C1332977"]
                        }
                    ]
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
                            "share_alike": False
                        }
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
                            "share_alike": False
                        }
                    },
                    "DO": {
                        "data_license": "CC0 1.0",
                        "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",  # noqa: E501
                        "version": "20210305",
                        "data_url": "http://www.obofoundry.org/ontology/doid.html",  # noqa: E501
                        "rdp_url": None,
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": False,
                            "share_alike": False
                        }
                    }
                },
                "service_meta_": {
                    'name': 'disease-normalizer',
                    'version': '0.1.0',
                    'response_datetime': '2021-04-05T16:44:15.367831',
                    'url': 'https://github.com/cancervariants/disease-normalization'  # noqa: E501
                }
            }


class SearchService(BaseModel):
    """Core response schema containing matches for each source"""

    query: str
    warnings: Optional[Dict]
    source_matches: Union[Dict[SourceName, MatchesKeyed], List[MatchesListed]]
    service_meta_: ServiceMeta

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['SearchService']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {
                "query": "Von Hippel-Lindau Syndrome",
                "warnings": None,
                "source_matches": [{
                    "source": "NCIt",
                    "match_type": 80,
                    "records": [{
                        "label": "Von Hippel-Lindau Syndrome",
                        "concept_id": "ncit:C3105",
                        "aliases": [
                            "Von Hippel-Lindau Syndrome (VHL)",
                            "Von Hippel-Lindau Disease",
                            "Cerebroretinal Angiomatosis",
                            "von Hippel-Lindau syndrome",
                            "VHL syndrome"
                        ],
                        "xrefs": [],
                        "associated_with": ["umls:C0019562"],
                        "pediatric_disease": None,
                    }],
                    "source_meta_": {
                        "data_license": "CC BY 4.0",
                        "data_license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
                        "version": "21.01d",
                        "data_url": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa: E501
                        "rdp_url": "http://reusabledata.org/ncit.html",
                        "data_license_attributes": {
                            "non_commercial": False,
                            "attribution": True,
                            "share_alike": False
                        }
                    }
                }],
                "service_meta_": {
                    'name': 'disease-normalizer',
                    'version': '0.1.0',
                    'response_datetime': '2021-04-05T16:44:15.367831',
                    'url': 'https://github.com/cancervariants/disease-normalization'  # noqa: E501
                }
            }
