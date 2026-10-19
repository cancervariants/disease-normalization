"""Get NCIt disease data."""

import logging
import re

import owlready2 as owl
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

from disease.etl.base import OWLBase
from disease.schemas import NamespacePrefix, concept_id_to_coding

_logger = logging.getLogger(__name__)

icdo_re = re.compile("[0-9]+/[0-9]+")


class NCIt(OWLBase):
    """Gather and load data from NCIt."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = DataSet(
            name=self._src_name,
            version=self._version,
            license=MappableConcept(
                name="CC BY 4.0",
                primaryCoding=Coding(
                    code=code(root="CC-BY-4.0"),
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
                    name="data_url", value="https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/"
                ),
                Extension(name="rdp_url", value="http://reusabledata.org/ncit.html"),
            ],
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
        p310 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P310"
        retired = self._get_by_property_value(p310, "Retired_Concept", graph)
        c22187 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C22187"
        nonhuman = self._get_subclasses(c22187, graph)
        return neopl.union(dos) - retired - nonhuman

    def _transform_data(self) -> None:
        """Get data from file and construct object for loading."""
        ncit = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        disease_uris = self._get_disease_classes()
        for uri in tqdm(disease_uris, ncols=80, disable=self._silent):
            disease_class = ncit.search(iri=uri)[0]
            concept_id = f"{NamespacePrefix.NCIT.value}:{disease_class.name}"
            if disease_class.P108:
                name = disease_class.P108.first()
            else:
                _logger.warning("No label for concept %s", concept_id)
                continue
            aliases = [a for a in disease_class.P90 if a != name]

            mappings = []
            if disease_class.P207:  # noqa: SIM102
                if coding := concept_id_to_coding(
                    f"{NamespacePrefix.UMLS.value}:{disease_class.P207.first()}"
                ):
                    mappings.append(
                        ConceptMapping(coding=coding, relation=Relation.RELATED_MATCH)
                    )
            maps_to = disease_class.P375
            if maps_to:
                icdo_list = list(filter(lambda s: icdo_re.match(s), maps_to))
                if len(icdo_list) == 1:  # noqa: SIM102
                    if coding := concept_id_to_coding(
                        f"{NamespacePrefix.ICDO.value}:{icdo_list[0]}"
                    ):
                        mappings.append(
                            ConceptMapping(
                                coding=coding, relation=Relation.RELATED_MATCH
                            )
                        )

            imdrf = disease_class.hasDbXref
            if imdrf:  # noqa: SIM102
                if coding := concept_id_to_coding(
                    f"{NamespacePrefix.IMDRF.value}:{imdrf[0].split(':')[1]}"
                ):
                    mappings.append(
                        ConceptMapping(coding=coding, relation=Relation.RELATED_MATCH)
                    )

            disease = MappableConcept(
                id=concept_id,
                primaryCoding=concept_id_to_coding(concept_id),
                name=name,
                aliases=aliases,
            )
            self._load_disease(disease)
