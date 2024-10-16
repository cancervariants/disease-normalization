"""Get OncoTree data."""

import json
import logging

from tqdm import tqdm

from disease.etl.base import Base
from disease.schemas import NamespacePrefix, SourceMeta

_logger = logging.getLogger(__name__)


class OncoTree(Base):
    """Gather and load data from OncoTree."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # F401
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

    def _traverse_tree(self, disease_node: dict) -> None:
        """Traverse JSON tree and queue diseases for loading where possible.

        :param disease_node: node in tree containing info for individual disease.
        """
        if disease_node["level"] >= 2:
            self._nodes.append(
                {
                    "code": disease_node["code"],
                    "name": disease_node["name"],
                    "externalReferences": disease_node.get("externalReferences", []),
                }
            )
        if disease_node.get("children"):
            for child in disease_node["children"].values():
                self._traverse_tree(child)

    def _add_disease(self, disease_node: dict) -> None:
        """Grab data from disease node and load into DB.

        :param disease_node: individual node taken from OncoTree tree
        """
        disease = {
            "concept_id": f"{NamespacePrefix.ONCOTREE.value}:{disease_node['code']}",
            "label": disease_node["name"],
            "xrefs": [],
            "associated_with": [],
            "oncologic_disease": True,
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
                _logger.warning("Unrecognized prefix: %s", prefix)
                continue
        self._load_disease(disease)

    def _transform_data(self) -> None:
        """Initiate OncoTree data transformation."""
        with self._data_file.open() as f:
            oncotree = json.load(f)
        self._nodes = []
        self._traverse_tree(oncotree["TISSUE"])
        for node in tqdm(self._nodes, ncols=80, disable=self._silent):
            self._add_disease(node)
