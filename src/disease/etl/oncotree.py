"""Get OncoTree data."""

import json
import logging

from ga4gh.core.models import (
    Coding,
    ConceptMapping,
    Extension,
    MappableConcept,
    Relation,
    code,
    iriReference,
)
from ga4gh.va_spec.base import DataSet
from tqdm import tqdm

from disease.etl.base import Base
from disease.schemas import NamespacePrefix, concept_id_to_coding

_logger = logging.getLogger(__name__)


class OncoTree(Base):
    """Gather and load data from OncoTree."""

    min_level = 2

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = DataSet(
            name=self._src_name,
            version=self._version,
            license=MappableConcept(
                name="CC BY 4.0",
                primaryCoding=Coding(
                    code=code(root="CC BY 4.0"),
                    system="https://spdx.org/licenses/",
                    iris=[
                        iriReference(
                            root="https://creativecommons.org/licenses/by/4.0/legalcode"
                        )
                    ],
                ),
                extensions=[
                    Extension(
                        name="license_attributes",
                        value={
                            "non_commercial": False,
                            "share_alike": False,
                            "attribution": True,
                        },
                    ),
                ],
            ),
            extensions=[
                Extension(
                    name="data_url",
                    value="http://oncotree.mskcc.org/#/home?tab=api",
                ),
            ],
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _traverse_tree(self, disease_node: dict) -> None:
        """Traverse JSON tree and queue diseases for loading where possible.

        :param disease_node: node in tree containing info for individual disease.
        """
        if disease_node["level"] >= self.min_level:
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
        concept_id = f"{NamespacePrefix.ONCOTREE.value}:{disease_node['code']}"
        refs = disease_node.get("externalReferences", [])
        mappings = []
        for prefix, codes in refs.items():
            if prefix == "UMLS":
                normed_prefix = NamespacePrefix.UMLS.value
                for umls_code in codes:
                    if umls_coding := concept_id_to_coding(
                        f"{normed_prefix}:{umls_code}"
                    ):
                        mappings.append(  # noqa: PERF401
                            ConceptMapping(
                                relation=Relation.RELATED_MATCH, coding=umls_coding
                            )
                        )
            elif prefix == "NCI":
                normed_prefix = NamespacePrefix.NCIT.value
                for nci_code in codes:
                    if nci_coding := concept_id_to_coding(
                        f"{normed_prefix}:{nci_code}"
                    ):
                        mappings.append(  # noqa: PERF401
                            ConceptMapping(
                                relation=Relation.EXACT_MATCH,
                                coding=nci_coding,
                            )
                        )
            else:
                _logger.warning(
                    "Unrecognized prefix in Oncotree ingest: %s [in %s]",
                    prefix,
                    concept_id,
                )
                continue
        primary_coding = concept_id_to_coding(concept_id)
        disease = MappableConcept(
            id=concept_id,
            primaryCoding=primary_coding,
            conceptType="disease",
            name=disease_node["name"],
            mappings=mappings,
            extensions=[Extension(name="oncologic_disease", value=True)],
        )
        self._load_disease(disease)

    def _transform_data(self) -> None:
        """Initiate OncoTree data transformation."""
        with self._data_file.open() as f:
            oncotree = json.load(f)
        self._nodes = []
        self._traverse_tree(oncotree["TISSUE"])
        for node in tqdm(self._nodes, ncols=80, disable=self._silent):
            self._add_disease(node)
