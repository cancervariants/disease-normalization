"""Get Human Disease Ontology data."""

import owlready2 as owl
from tqdm import tqdm

from disease import PREFIX_LOOKUP
from disease.etl.base import OWLBase
from disease.schemas import NamespacePrefix, SourceMeta

DO_PREFIX_LOOKUP = {
    "EFO": NamespacePrefix.EFO.value,
    "GARD": NamespacePrefix.GARD.value,
    "ICDO": NamespacePrefix.ICDO.value,
    "MESH": NamespacePrefix.MESH.value,
    "NCI": NamespacePrefix.NCIT.value,
    "ORDO": NamespacePrefix.ORPHANET.value,
    "UMLS_CUI": NamespacePrefix.UMLS.value,
    "ICD9CM": NamespacePrefix.ICD9CM.value,
    "ICD10CM": NamespacePrefix.ICD10CM.value,
    "MIM": NamespacePrefix.OMIM.value,
    "KEGG": NamespacePrefix.KEGG.value,
    "MEDDRA": NamespacePrefix.MEDDRA.value,
}


class DO(OWLBase):
    """Disease Ontology ETL class."""

    def _load_meta(self) -> None:
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC0 1.0",
            data_license_url="https://creativecommons.org/publicdomain/zero/1.0/legalcode",
            version=self._version,
            data_url="http://www.obofoundry.org/ontology/doid.html",
            rdp_url=None,
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": False,
            },
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _transform_data(self) -> None:
        """Transform source data and send to loading method."""
        do = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        disease_uri = "http://purl.obolibrary.org/obo/DOID_4"
        diseases = self._get_subclasses(
            disease_uri, owl.default_world.as_rdflib_graph()
        )
        for uri in tqdm(diseases, ncols=80, disable=self._silent):
            disease_class = do.search(iri=uri)[0]
            if disease_class.deprecated:
                continue

            concept_id = f"{NamespacePrefix.DO.value}:{uri.split('_')[-1]}"
            label = disease_class.label[0]

            synonyms = disease_class.hasExactSynonym
            aliases = list({s for s in synonyms if s != label}) if synonyms else []

            xrefs = []
            associated_with = []
            db_associated_with = set(disease_class.hasDbXref)
            for xref in db_associated_with:
                prefix, id_no = xref.split(":", 1)
                normed_prefix = DO_PREFIX_LOOKUP.get(prefix)
                if normed_prefix:
                    xref_no = f"{normed_prefix}:{id_no}"
                    if normed_prefix.lower() in PREFIX_LOOKUP:
                        if normed_prefix == NamespacePrefix.OMIM and id_no.startswith(
                            "PS"
                        ):
                            associated_with.append(xref_no)
                        else:
                            xrefs.append(xref_no)
                    else:
                        associated_with.append(xref_no)

            disease = {
                "concept_id": concept_id,
                "label": label,
                "aliases": aliases,
                "xrefs": xrefs,
                "associated_with": associated_with,
            }
            self._load_disease(disease)
