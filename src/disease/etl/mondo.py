"""Module to load disease data from Mondo Disease Ontology."""
import logging
from collections import defaultdict
from typing import DefaultDict, Optional, Set

import fastobo

from disease.etl.base import Base
from disease.schemas import NamespacePrefix, SourceMeta

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
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": True,
            },
        )
        self._database.add_source_metadata(self._src_name, metadata)

    @staticmethod
    def _process_xref(xref: fastobo.xref.Xref) -> Optional[str]:
        """From xref clause, format xref concept ID

        :param xref: xref clause from OBO file frame
        :return: processed xref string if namespace is recognized
        """
        try:
            prefix = NamespacePrefix[xref.id.prefix.upper()]
        except KeyError:
            _logger.warning(f"Unrecognized namespace: {xref.id.prefix}")
            print(xref)
            return None
        return f"{prefix}:{xref.id.local}"

    def _construct_dependency_set(self, dag: DefaultDict, parent: str) -> Set[str]:
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

        reader = fastobo.iter(str(self._data_file.absolute()))
        for item in reader:
            concept_id = str(item.id).lower()
            if concept_id.upper() not in diseases:
                continue

            params = {
                "concept_id": str(item.id).lower(),
                "aliases": [],
                "xrefs": [],
            }
            for clause in item:
                tag = clause.raw_tag()
                if tag == "name":
                    params["label"] = clause.raw_value()
                elif tag == "synonym":
                    params["aliases"].append(clause.synonym.desc)
                elif tag == "xref":
                    xref = self._process_xref(clause.xref)
                    if xref:
                        params["xrefs"].append(xref)

            if concept_id.upper() in pediatric_diseases:
                params["pediatric_disease"] = True

            self._load_disease(params)
