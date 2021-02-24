"""This module contains data models for representing VICC normalized
disease records.
"""
from typing import Any, Dict, Type, List, Optional, Union
from enum import Enum, IntEnum
from pydantic import BaseModel, StrictBool


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    LABEL = 80
    ALIAS = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(Enum):
    """Define string constraints to ensure consistent capitalization."""

    NCIT = "NCIt"
    MONDO = "Mondo"
    DO = "DO"


class SourceIDAfterNamespace(Enum):
    """Define string constraints after namespace."""

    NCIT = "C"
    MONDO = ""
    DO = ""


class NamespacePrefix(Enum):
    """Define string constraints for how concept ID namespace prefixes are
    stored.
    """

    # built-in sources
    NCIT = "ncit"
    MONDO = "mondo"
    DO = "DOID"
    # external sources
    COHD = "cohd"
    EFO = "efo"
    GARD = "gard"
    HPO = "HP"
    ICD9 = "icd9"
    ICD9CM = "icd9.cm"
    ICD10 = "icd"
    ICD10CM = "icd10.cm"
    ICDO = "icd.o"
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
    OMIM = "omim"
    OMIMPS = "omimps"
    ONCOTREE = "oncotree"
    ORPHANET = "orphanet"
    PATO = "pato"
    UMLS = "umls"
    WIKIPEDIA = "wikipedia.en"
    WIKIDATA = "wikidata"


class SourcePriority(IntEnum):
    """Define priorities for sources in building merged concepts."""

    NCIT = 1
    MONDO = 2
    DO = 3


class Disease(BaseModel):
    """Define disease record."""

    label: str
    concept_id: str
    aliases: Optional[List[str]]
    other_identifiers: Optional[List[str]]
    xrefs: Optional[List[str]]
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
                "other_identifiers": [],
                "xrefs": ["umls:C0019562"],
                "pediatric_disease": None,
            }


class DataLicenseAttributes(BaseModel):
    """Define constraints for data license attributes."""

    non_commercial: StrictBool
    share_alike: StrictBool
    attribution: StrictBool


class Meta(BaseModel):
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
                         model: Type['Meta']) -> None:
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
    meta_: Meta

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
                    "other_identifiers": [],
                    "xrefs": ["umls:C0019562"],
                    "pediatric_disease": None,
                }],
                "meta_": {
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
    meta_: Meta

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
                    "other_identifiers": [],
                    "xrefs": ["umls:C0019562"],
                    "pediatric_disease": None
                }],
                "meta_": {
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


class MergedMatch(BaseModel):
    """Represent merged concept in response to client."""

    label: Optional[str]
    concept_ids: List[str]
    aliases: Optional[List[str]]
    xrefs: Optional[List[str]]
    pediatric_disease: Optional[bool]

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['MergedMatch']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {}  # TODO


class NormalizationService(BaseModel):
    """Response containing one or more merged records and source data."""

    query: str
    warnings: Optional[Dict]
    match_type: MatchType
    record: Optional[MergedMatch]
    meta_: Optional[Dict[SourceName, Meta]]

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['NormalizationService']) -> None:
            """Configure OpenAPI schema"""
            if 'title' in schema.keys():
                schema.pop('title', None)
            for prop in schema.get('properties', {}).values():
                prop.pop('title', None)
            schema['example'] = {}  # TODO


class Service(BaseModel):
    """Core response schema containing matches for each source"""

    query: str
    warnings: Optional[Dict]
    source_matches: Union[Dict[SourceName, MatchesKeyed], List[MatchesListed]]

    class Config:
        """Enables orm_mode"""

        @staticmethod
        def schema_extra(schema: Dict[str, Any],
                         model: Type['Service']) -> None:
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
                        "other_identifiers": [],
                        "xrefs": ["umls:C0019562"],
                        "pediatric_disease": None,
                    }],
                    "meta_": {
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
                }]
            }
