"""Module to load disease data from OncoTree."""
import json
from typing import Dict

from disease import logger
from disease.etl.base import Base
from disease.schemas import Disease, NamespacePrefix, SourceMeta


class OncoTree(Base):
    """Gather and load data from OncoTree."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
            version=self._version,
            data_url="http://oncotree.mskcc.org/#/home?tab=api",
            rdp_url=None,
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": True,
            },
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _traverse_tree(self, disease_node: Dict) -> None:
        """Traverse JSON tree and load diseases where possible.

        :param Dict disease_node: node in tree containing info for individual
            disease.
        """
        if disease_node.get("level", None) >= 2:
            disease = {
                "concept_id": f"{NamespacePrefix.ONCOTREE.value}:{disease_node['code']}",
                "label": disease_node["name"],
                "xrefs": [],
                "associated_with": [],
            }
            refs = disease_node.get("externalReferences", [])
            for prefix, codes in refs.items():
                if prefix == "UMLS":
                    normed_prefix = NamespacePrefix.UMLS.value
                    for code in codes:
                        normed_id = f"{normed_prefix}:{code}"
                        disease["associated_with"].append(normed_id)
                elif prefix == "NCI":
                    normed_prefix = NamespacePrefix.NCIT.value
                    for code in codes:
                        normed_id = f"{normed_prefix}:{code}"
                        disease["xrefs"].append(normed_id)
                else:
                    logger.warning(f"Unrecognized prefix: {prefix}")
                    continue
            assert Disease(**disease)
            self._load_disease(disease)
        if disease_node.get("children", None):
            for child in disease_node["children"].values():
                self._traverse_tree(child)

    def _transform_data(self) -> None:
        """Initiate OncoTree data transformation."""
        with open(self._data_file, "r") as f:
            oncotree = json.load(f)
        self._traverse_tree(oncotree["TISSUE"])
