"""This module contains data models for representing VICC normalized
disease records.
"""
from typing import Any, Dict, Type, List, Optional, StrictBool, Union
from enum import Enum, IntEnum
from pydantic import BaseModel


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    NAME = 80
    ALIAS = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(Enum):
    """Define string constraints to ensure consistent capitalization."""

    NCIT = "NCIt"


class SourceIDAfterNamespace(Enum):
    """Define string constraints after namespace."""

    NCIT = "C"  # TODO double check that this is accurate


class NamespacePrefix(Enum):
    """Define string constraints for namespace prefixes on concept IDs."""

    NCIT = "ncit"


class Disease(BaseModel):
    """Define disease record."""

    label: str
    concept_id: str
    aliases: Optional[List[str]]
    other_identifiers: Optional[List[str]]
    xrefs: Optional[List[str]]

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
            # TODO example


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
            # schema['example'] = {
            #     'data_license': 'CC BY-SA 3.0',
            #     'data_license_url':
            #         'https://creativecommons.org/licenses/by-sa/3.0/',
            #     'version': '27',
            #     'data_url':
            #         'http://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_27/',  # noqa: E501
            #     'rdp_url': 'http://reusabledata.org/chembl.html',
            #     'data_license_attributes': {
            #         'non_commercial': False,
            #         'share_alike': True,
            #         'attribution': True
            #     }
            # }


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
            # schema['example'] = {
            #     'match_type': 0,
            #     'records': [],
            #     'meta_': {
            #         'data_license': 'CC BY-SA 3.0',
            #         'data_license_url':
            #             'https://creativecommons.org/licenses/by-sa/3.0/',
            #         'version': '27',
            #         'data_url':
            #             'http://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_27/',  # noqa: E501
            #         'rdp_url': 'http://reusabledata.org/chembl.html',
            #         'data_license_attributes': {
            #             'non_commercial': False,
            #             'share_alike': True,
            #             'attribution': True
            #         }
            #     },
            # }


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
            # schema['example'] = {
            #     'normalizer': 'ChEMBL',
            #     'match_type': 0,
            #     'records': [],
            #     'meta_': {
            #         'data_license': 'CC BY-SA 3.0',
            #         'data_license_url':
            #             'https://creativecommons.org/licenses/by-sa/3.0/',
            #         'version': '27',
            #         'data_url':
            #             'http://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_27/',  # noqa: E501
            #         'rdp_url': 'http://reusabledata.org/chembl.html',
            #         'data_license_attributes': {
            #             'non_commercial': False,
            #             'share_alike': True,
            #             'attribution': True
            #         }
            #     },
            # }


class DataLicenseAttributes(BaseModel):
    """Define constraints for data license attributes."""

    non_commercial: StrictBool
    share_alike: StrictBool
    attribution: StrictBool


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
            # schema['example'] = {
            #     'query': 'CISPLATIN',
            #     'warnings': None,
            #     'meta_': {
            #         'data_license': 'CC BY-SA 3.0',
            #         'data_license_url':
            #             'https://creativecommons.org/licenses/by-sa/3.0/',
            #         'version': '27',
            #         'data_url':
            #             'http://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_27/',  # noqa: E501
            #         'rdp_url': 'http://reusabledata.org/chembl.html',
            #         'data_license_attributes': {
            #             'non_commercial': False,
            #             'share_alike': True,
            #             'attribution': True
            #         }
            #     }
            # }
