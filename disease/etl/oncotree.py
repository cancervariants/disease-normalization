"""Module to load disease data from OncoTree."""
import json

from disease import logger
from disease.schemas import Disease, NamespacePrefix, SourceMeta, SourceName

from .base import Base


class OncoTree(Base):
    """Gather and load data from OncoTree."""

    def _download_data(self):
        """Download Oncotree source data for loading into normalizer."""
        logger.info("Retrieving source data for OncoTree")
        url_version = self._version.replace("-", "_")
        url = f"http://oncotree.mskcc.org/api/tumorTypes/tree?version=oncotree_{url_version}"  # noqa: E501
        output_file = self._src_dir / f"oncotree_{self._version}.json"
        self._http_download(url, output_file)
        logger.info("Successfully retrieved source data for OncoTree")

    def _load_meta(self):
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",
            version=self._version,
            data_url="http://oncotree.mskcc.org/#/home?tab=api",
            rdp_url=None,
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": True,
            },
        )
        params = dict(metadata)
        params["src_name"] = SourceName.ONCOTREE.value
        self.database.metadata.put_item(Item=params)

    def _traverse_tree(self, disease_node):
        """Traverse JSON tree and load diseases where possible.

        :param Dict disease_node: node in tree containing info for individual
            disease.
        """
        if disease_node.get("level", None) >= 2:
            disease = {
                "concept_id": f"{NamespacePrefix.ONCOTREE.value}:{disease_node['code']}",  # noqa: E501
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

    def _transform_data(self):
        """Initiate OncoTree data transformation."""
        with open(self._data_file, "r") as f:
            oncotree = json.load(f)
        self._traverse_tree(oncotree["TISSUE"])
