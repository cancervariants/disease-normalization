"""Get NCIt disease data."""

import logging
import re

import owlready2 as owl
from tqdm import tqdm

from disease.etl.base import OWLBase
from disease.schemas import NamespacePrefix, SourceMeta, SourceName

_logger = logging.getLogger(__name__)

icdo_re = re.compile("[0-9]+/[0-9]+")


class NCIt(OWLBase):
    """Gather and load data from NCIt."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # F401
            version=self._version,
            data_url="https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/",
            rdp_url="http://reusabledata.org/ncit.html",
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": True,
            },
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _get_disease_classes(self) -> set[str]:
        """Get all nodes with semantic_type 'Neoplastic Process' or 'Disease
        or Syndrome'.

        :return: uq_nodes with additions from above types added
        :rtype: Set[str]
        """
        graph = owl.default_world.as_rdflib_graph()
        p106 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        neopl = self._get_by_property_value(p106, "Neoplastic Process", graph)
        dos = self._get_by_property_value(p106, "Disease or Syndrome", graph)
        p310 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        retired = self._get_by_property_value(p310, "Retired_Concept", graph)
        return neopl.union(dos) - retired

    def _transform_data(self) -> None:
        """Get data from file and construct object for loading."""
        ncit = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        disease_uris = self._get_disease_classes()
        for uri in tqdm(disease_uris, ncols=80, disable=self._silent):
            disease_class = ncit.search(iri=uri)[0]
            concept_id = f"{NamespacePrefix.NCIT.value}:{disease_class.name}"
            if disease_class.P108:
                label = disease_class.P108.first()
            else:
                _logger.warning("No label for concept %s", concept_id)
                continue
            aliases = [a for a in disease_class.P90 if a != label]

            associated_with = []
            if disease_class.P207:
                associated_with.append(
                    f"{NamespacePrefix.UMLS.value}:" f"{disease_class.P207.first()}"
                )
            maps_to = disease_class.P375
            if maps_to:
                icdo_list = list(filter(lambda s: icdo_re.match(s), maps_to))
                if len(icdo_list) == 1:
                    associated_with.append(
                        f"{NamespacePrefix.ICDO.value}:" f"{icdo_list[0]}"
                    )
            imdrf = disease_class.hasDbXref
            if imdrf:
                associated_with.append(
                    f"{NamespacePrefix.IMDRF.value}:" f"{imdrf[0].split(':')[1]}"
                )

            disease = {
                "concept_id": concept_id,
                "src_name": SourceName.NCIT.value,
                "label": label,
                "aliases": aliases,
                "associated_with": associated_with,
            }
            self._load_disease(disease)
