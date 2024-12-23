"""Get Mondo Disease Ontology data."""

import logging
import re
from collections import defaultdict
from typing import ClassVar

import fastobo
from tqdm import tqdm

from disease.etl.base import Base
from disease.schemas import DataLicenseAttributes, NamespacePrefix, SourceMeta

_logger = logging.getLogger(__name__)


class Mondo(Base):
    """Gather and load data from Mondo."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",
            version=self._version,
            data_url="https://mondo.monarchinitiative.org/pages/download/",
            rdp_url="http://reusabledata.org/monarch.html",
            data_license_attributes=DataLicenseAttributes(
                non_commercial=False, share_alike=False, attribution=True
            ),
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _construct_dependency_set(self, dag: defaultdict, parent: str) -> set[str]:
        """Recursively get all children concepts for a term

        :param dag: dictionary where keys are ontology terms and values are lists of
            terms with ``is_a`` relationships to the parent
        :param parent: term to fetch children for
        :return: Set of children concepts
        """
        children = {parent}
        for child in dag[parent]:
            children |= self._construct_dependency_set(dag, child)
        return children

    _identifiers_url_pattern = r"http://identifiers.org/(.*)/(.*)"
    _lui_patterns: ClassVar = [
        # (NamespacePrefix.OMIMPS, r"https://omim.org/phenotypicSeries/(.*)"),
        (NamespacePrefix.OMIM, r"https://omim.org/entry/(.*)"),
        (NamespacePrefix.UMLS, r"http://linkedlifedata.com/resource/umls/id/(.*)"),
        (NamespacePrefix.ICD10CM, r"http://purl.bioontology.org/ontology/ICD10CM/(.*)"),
        (NamespacePrefix.ICD10, r"https://icd.who.int/browse10/2019/en#/(.*)"),
    ]

    def _get_xref_from_url(self, url: str) -> tuple[NamespacePrefix, str] | None:
        """Extract prefix and LUI from URL reference.

        :param url: url string given as URL xref property
        :return: prefix enum instance and LUI
        """
        if url.startswith("http://identifiers.org"):
            match = re.match(self._identifiers_url_pattern, url)
            if not match or not match.groups():
                msg = f"Couldn't parse identifiers.org URL: {url}"
                raise ValueError(msg)
            if match.groups()[0] == "snomedct":
                return None
            prefix = NamespacePrefix[match.groups()[0].upper()]
            return (prefix, match.groups()[1])
        for prefix, pattern in self._lui_patterns:
            match = re.match(pattern, url)
            if match and match.groups():
                return (prefix, match.groups()[0])
        # didn't match any patterns
        _logger.warning("Unrecognized URL for xref: %s", url)
        return None

    @staticmethod
    def _get_xref_from_xref_clause(
        clause: fastobo.term.XrefClause,
    ) -> tuple[NamespacePrefix, str] | None:
        """Get dbXref from xref clause.

        In the Mondo OBO distribution, some xrefs only show up in explicit xref clauses.
        This method processes them.

        :param clause: xref clause from term frame
        :return: prefix and local ID if available
        """
        raw_prefix = clause.xref.id.prefix
        if raw_prefix not in ("ONCOTREE", "EFO"):
            return None
        try:
            prefix = NamespacePrefix[clause.xref.id.prefix.upper()]
        except KeyError:
            _logger.warning("Unable to parse namespace prefix for %s", clause.xref)
            return None
        local_id = clause.xref.id.local
        return prefix, local_id

    def _get_xref_from_pv_clause(
        self, clause: fastobo.term.PropertyValueClause
    ) -> tuple[NamespacePrefix, str] | None:
        """Get dbXref from property value clause.

        These are a bit more semantically rich than the Mondo xref clauses, so for now,
        we prefer to fetch most references from here.

        :param clause: property value clause
        :return: prefix and local ID if available
        """
        property_value = clause.property_value
        # of all property values, all we care about are those which are skos:exactMatch,
        # so we can ignore other relations and any non-resource property values.
        # previously there may have been usage of mondo:equivalentTo but that seems to
        # be irrelevant for property values
        if not isinstance(
            property_value, fastobo.pv.ResourcePropertyValue
        ) or property_value.relation != fastobo.id.PrefixedIdent("skos", "exactMatch"):
            return None
        if isinstance(property_value.value, fastobo.id.Url):
            xref_result = self._get_xref_from_url(str(property_value.value))
            if xref_result is None:
                return None
            prefix, local_id = xref_result
        elif isinstance(property_value.value, fastobo.id.PrefixedIdent):
            prefix = NamespacePrefix[property_value.value.prefix.upper()]
            local_id = property_value.value.local
        else:
            _logger.warning(
                "Unrecognized property value type: %s", type(property_value.value)
            )
            return None
        return prefix, local_id

    def _process_term_frame(self, frame: fastobo.term.TermFrame) -> dict:
        """Extract disease params from an OBO term frame.

        :param frame: individual frame from OBO file
        :return: disease params as a dictionary
        """
        params = {
            "concept_id": str(frame.id).lower(),
            "aliases": [],
            "xrefs": [],
            "associated_with": [],
        }

        for clause in frame:
            tag = clause.raw_tag()
            if tag == "name":
                params["label"] = clause.raw_value()
            elif tag == "synonym":
                params["aliases"].append(clause.synonym.desc)
            elif tag in ("xref", "property_value"):
                if tag == "xref":
                    xref = self._get_xref_from_xref_clause(clause)
                else:
                    xref = self._get_xref_from_pv_clause(clause)
                if not xref:
                    continue
                prefix, local_id = xref

                curie = f"{prefix.value}:{local_id}"
                if prefix in (
                    NamespacePrefix.OMIM,
                    NamespacePrefix.NCIT,
                    NamespacePrefix.DO,
                    NamespacePrefix.ONCOTREE,
                ):
                    params["xrefs"].append(curie)
                else:
                    params["associated_with"].append(curie)
        return params

    def _transform_data(self) -> None:
        """Get data from file and send disease records to database."""
        reader = fastobo.iter(str(self._data_file.absolute()))
        dag = defaultdict(list)
        for item in reader:
            item_id = str(item.id)
            for clause in item:
                if clause.raw_tag() == "is_a":
                    dag[clause.raw_value()].append(item_id)

        disease_root = "MONDO:0000001"
        diseases = self._construct_dependency_set(dag, disease_root)
        peds_neoplasm_root = "MONDO:0006517"
        pediatric_diseases = self._construct_dependency_set(dag, peds_neoplasm_root)
        cancer_root = "MONDO:0045024"
        cancers = self._construct_dependency_set(dag, cancer_root)

        reader = fastobo.iter(str(self._data_file.absolute()))
        for item in tqdm(reader, ncols=80, disable=self._silent):
            concept_id = str(item.id).lower()
            if concept_id.upper() not in diseases:
                continue

            params = self._process_term_frame(item)

            if concept_id.upper() in pediatric_diseases:
                params["pediatric_disease"] = True

            if concept_id.upper() in cancers:
                params["oncologic_disease"] = True

            self._load_disease(params)
