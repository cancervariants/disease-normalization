"""Contains data models for representing VICC normalized disease records."""

import datetime as dt
import logging
from enum import Enum, IntEnum, StrEnum
from types import MappingProxyType
from typing import Literal

from ga4gh.core.models import (
    Coding,
    ConceptMapping,
    Extension,
    MappableConcept,
    Relation,
    code,
)
from ga4gh.va_spec.base import DataSet
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr

from disease import __version__

_logger = logging.getLogger(__name__)


class MatchType(IntEnum):
    """Define string constraints for use in Match Type attributes."""

    CONCEPT_ID = 100
    LABEL = 80
    ALIAS = 60
    XREF = 60
    ASSOCIATED_WITH = 60
    FUZZY_MATCH = 20
    NO_MATCH = 0


class SourceName(StrEnum):
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


# use to fetch source name from schema based on concept id namespace
# e.g. {'ncit': 'NCIt', 'doid': 'DO'}
PREFIX_LOOKUP = {
    v.value.lower(): SourceName[k].value
    for k, v in NamespacePrefix.__members__.items()
    if k in SourceName.__members__
}

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


# use to generate namespace prefix from source ID value
# e.g. {'c': 'NCIt'}
NAMESPACE_LOOKUP = {
    v.value.lower(): NamespacePrefix[k].value
    for k, v in SourceIDAfterNamespace.__members__.items()
    if v.value != ""
}

# use to lookup source name from lower-case string
# technically the same as PREFIX_LOOKUP, but source namespace prefixes
# sometimes differ from their names
# e.g. {'ncit': 'NCIt'}
SOURCES_LOWER_LOOKUP = {
    name.value.lower(): name.value for name in SourceName.__members__.values()
}

DISEASE_CONCEPT_TYPE = "Disease"


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


class RecordType(StrEnum):
    """Record item types."""

    IDENTITY = "identity"
    MERGER = "merger"


class RefType(StrEnum):
    """Reference item types."""

    # Must be in descending MatchType order.
    LABEL = "label"
    ALIASES = "alias"
    XREFS = "xref"
    ASSOCIATED_WITH = "associated_with"


ITEM_TYPES = {k.lower(): v.value for k, v in RefType.__members__.items()}


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
    response_datetime: dt.datetime
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
                    "primaryCoding": {
                        "id": "ncit:C4989",
                        "code": "C4989",
                        "system": "https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?dictionary=NCI_Thesaurus&code=",
                    },
                    "conceptType": "Disease",
                    "name": "Childhood Leukemia",
                    "mappings": [
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


class ServiceEnvironment(StrEnum):
    """Define current runtime environment."""

    DEV = "dev"  # local dev
    TEST = "test"  # local/CI testing
    PROD = "prod"  # main production env on cloud
    STAGING = "staging"  # staging env on cloud


LAB_EMAIL = "Alex.Wagner@nationwidechildrens.org"
LAB_WEBPAGE_URL = "https://www.nationwidechildrens.org/specialties/institute-for-genomic-medicine/research-labs/wagner-lab"
DOCS_URL = "https://disease-normalizer.readthedocs.io/"
APP_DESCRIPTION = "Resolve ambiguous references and descriptions of human diseases to consistently-structured, normalized terms"


class ServiceType(BaseModel):
    """Define service_info response for type field"""

    group: Literal["org.genomicmedlab"] = "org.genomicmedlab"
    artifact: Literal["Disease Normalizer API"] = "Disease Normalizer API"
    version: Literal[__version__] = __version__


class ServiceOrganization(BaseModel):
    """Define service_info response for organization field"""

    name: Literal["Genomic Medicine Lab at Nationwide Children's Hospital"] = (
        "Genomic Medicine Lab at Nationwide Children's Hospital"
    )
    url: Literal[LAB_WEBPAGE_URL] = LAB_WEBPAGE_URL


class ServiceInfo(BaseModel):
    """Define response structure for GA4GH /service_info endpoint."""

    id: Literal["org.genomicmedlab.disease_normalizer"] = (
        "org.genomicmedlab.disease_normalizer"
    )
    name: Literal["disease_normalizer"] = "disease_normalizer"
    type: ServiceType
    description: Literal[APP_DESCRIPTION] = APP_DESCRIPTION
    organization: ServiceOrganization
    contactUrl: Literal[LAB_EMAIL] = LAB_EMAIL  # noqa: N815
    documentationUrl: Literal[DOCS_URL] = DOCS_URL  # noqa: N815
    createdAt: Literal["2021-01-01T00:00:00+00:00"] = "2021-01-01T00:00:00+00:00"  # noqa: N815
    updatedAt: Literal["2021-01-01T00:00:00+00:00"] = "2021-01-01T00:00:00+00:00"  # noqa: N815
    environment: ServiceEnvironment
    version: Literal[__version__] = __version__


class SourceMetadataError(Exception):
    """Raise for missing source metadata properties"""


class SourceDataSet(DataSet):
    """VA-Spec DataSet with helper methods added for extracting source metadata"""

    def get_data_license_url(self) -> str:
        """Return the URL describing the source's data license.

        :return: The first IRI in the license's primary coding.
        :raises SourceMetadataError: If no data license URL is available.
        """
        if (
            not self.license
            or not self.license.primaryCoding
            or not self.license.primaryCoding.iris
        ):
            msg = f"Source {self.name}: Data license URL is missing"
            raise SourceMetadataError(msg)
        return self.license.primaryCoding.iris[0].root

    def _get_str_extension(self, name: str) -> str:
        """Return the value of the first extension with the given name.

        :param name: Extension name to look up.
        :return: The extension value, expected to be a string.
        :raises SourceMetadataError: If no matching extension exists.
        """
        try:
            matching_ext = next(
                e for e in getattr(self, "extensions", []) if e.name == name
            )
        except StopIteration as e:
            msg = f"Source {self.name}: Extension {name} is missing"
            raise SourceMetadataError(msg) from e
        return matching_ext.value

    def get_data_url(self) -> str:
        """Return the source's data URL.

        :return: The value of the ``data_url`` extension.
        :raises SourceMetadataError: If the extension is missing.
        """
        return self._get_str_extension("data_url")

    def get_rdp_url(self) -> str | None:
        """Return the source's RDP URL.

        :return: The value of the ``rdp_url`` extension if available
        :raises SourceMetadataError: If the extension is missing.
        """
        try:
            return self._get_str_extension("rdp_url")
        except SourceMetadataError:
            return None  # RDP isn't always available

    def get_license_attributes(self) -> dict:
        """Return the source's structured data license attributes.

        :return: The value of the license's ``license_attributes`` extension.
        :raises SourceMetadataError: If license attributes are missing.
        """
        if not self.license or not self.license.extensions:
            msg = f"Source {self.name}: license attributes are missing"
            raise SourceMetadataError(msg)
        try:
            matching_ext = next(
                e for e in self.license.extensions if e.name == "license_attributes"
            )
        except StopIteration as e:
            msg = f"Source {self.name}: license attributes are missing"
            raise SourceMetadataError(msg) from e
        return matching_ext.value


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


def concept_id_to_coding(concept_id: str) -> Coding | None:
    """Construct instance from a concept ID"""
    raw_prefix, source_code = concept_id.split(":")

    try:
        prefix = NamespacePrefix(raw_prefix)
    except ValueError:
        try:
            prefix = NamespacePrefix(raw_prefix.upper())
        except ValueError:
            _logger.info(
                "Namespace prefix not supported: %s [in %s]", raw_prefix, concept_id
            )
            return None

    id_ = concept_id

    if prefix == NamespacePrefix.MONDO:
        source_code = concept_id.upper()
        id_ = source_code.replace(":", "_")
    elif prefix == NamespacePrefix.DOID:
        source_code = concept_id

    return Coding(
        id=id_,
        code=code(source_code),
        system=NAMESPACE_TO_SYSTEM_URI[prefix],
    )


def coding_to_concept_id(coding: Coding) -> str:
    """Get concept ID from coding object"""
    if coding.system == NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.MONDO]:
        return coding.id.replace("_", ":").lower()
    if coding.system == NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.DOID]:
        return coding.code.root
    return coding.id


def mapcon_to_disease(disease: MappableConcept) -> Disease:
    """Construct old-style disease record from a disease mappableconcept

    This is a temporary function to help transition from the old disease class --
    once these efforts are complete, this method will go away

    It will definitely get used redundantly to preserve APIs between pull requests,
    and at the end should unwind cleanly
    """
    aw = []
    xrefs = []
    if disease.mappings:
        for mapping in disease.mappings:
            if mapping.coding.system in {
                NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.ONCOTREE],
                NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.DO],
                NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.OMIM],
                NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.NCIT],
                NAMESPACE_TO_SYSTEM_URI[NamespacePrefix.MONDO],
            }:
                xrefs.append(mapping.coding.id)
            else:
                aw.append(mapping.coding.id)
    is_ped_disease = None
    is_onco_disease = None
    if disease.extensions:
        for ext in disease.extensions:
            if ext.name == "oncologic_disease":
                is_onco_disease = ext.value
            elif ext.name == "pediatric_disease":
                is_ped_disease = ext.value
    return Disease(
        concept_id=coding_to_concept_id(disease.primaryCoding),
        label=disease.name,
        aliases=disease.aliases or [],
        associated_with=aw,
        xrefs=xrefs,
        pediatric_disease=is_ped_disease,
        oncologic_disease=is_onco_disease,
    )


def disease_to_mapcon(disease: Disease) -> MappableConcept:
    """Get mappable concept from disease record

    This function is temporary (see above)
    """
    extensions = []
    if disease.pediatric_disease:
        extensions.append(Extension(name="pediatric_disease", value=True))
    if disease.oncologic_disease:
        extensions.append(Extension(name="oncologic_disease", value=True))
    mappings = []
    mappings.extend(
        ConceptMapping(relation=Relation.EXACT_MATCH, coding=concept_id_to_coding(xref))
        for xref in disease.xrefs
    )
    mappings.extend(
        ConceptMapping(relation=Relation.RELATED_MATCH, coding=concept_id_to_coding(aw))
        for aw in disease.associated_with
    )
    return MappableConcept(
        id=disease.concept_id,
        primaryCoding=concept_id_to_coding(disease.concept_id),
        extensions=extensions,
        aliases=disease.aliases,
        mappings=mappings,
    )
