"""Disease Ontology ETL module."""
import owlready2 as owl
import bioversions

from disease import PREFIX_LOOKUP, logger
from disease.schemas import SourceMeta, SourceName, NamespacePrefix
from disease.etl.base import OWLBase


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
    "OMIM": NamespacePrefix.OMIM.value,
    "KEGG": NamespacePrefix.KEGG.value,
    "MEDDRA": NamespacePrefix.MEDDRA.value,
}


class DO(OWLBase):
    """Disease Ontology ETL class."""

    def get_latest_version(self) -> str:
        """Get most recent version of source data. Should be overriden by
        sources not added to Bioversions yet, or other special-case sources.
        :return: most recent version, as a str
        """
        return bioversions.get_version("disease ontology")

    def _download_data(self):
        """Download DO source file for loading into normalizer."""
        logger.info('Retrieving source data for Disease Ontology')
        output_file = self._src_dir / f"do_{self._version}.owl"
        self._http_download("http://purl.obolibrary.org/obo/doid/doid-merged.owl",
                            output_file)
        logger.info("Successfully retrieved source data for Disease Ontology")

    def _load_meta(self):
        """Load metadata"""
        metadata_params = {
            "data_license": "CC0 1.0",
            "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",  # noqa: E501
            "version": self._version,
            "data_url": "http://www.obofoundry.org/ontology/doid.html",
            "rdp_url": None,
            "data_license_attributes": {
                "non_commercial": False,
                "share_alike": False,
                "attribution": False
            }
        }
        assert SourceMeta(**metadata_params)
        metadata_params['src_name'] = SourceName.DO.value
        self.database.metadata.put_item(Item=metadata_params)

    def _transform_data(self):
        """Transform source data and send to loading method."""
        do = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        disease_uri = 'http://purl.obolibrary.org/obo/DOID_4'
        diseases = self._get_subclasses(
            disease_uri, owl.default_world.as_rdflib_graph()
        )
        for uri in diseases:
            disease_class = do.search(iri=uri)[0]
            if disease_class.deprecated:
                continue

            concept_id = f"{NamespacePrefix.DO.value}:{uri.split('_')[-1]}"
            label = disease_class.label[0]

            synonyms = disease_class.hasExactSynonym
            if synonyms:
                aliases = list({s for s in synonyms if s != label})
            else:
                aliases = []

            xrefs = []
            associated_with = []
            db_associated_with = set(disease_class.hasDbXref)
            for xref in db_associated_with:
                prefix, id_no = xref.split(':', 1)
                normed_prefix = DO_PREFIX_LOOKUP.get(prefix, None)
                if normed_prefix:
                    xref_no = f'{normed_prefix}:{id_no}'
                    if normed_prefix.lower() in PREFIX_LOOKUP:
                        xrefs.append(xref_no)
                    else:
                        associated_with.append(xref_no)

            disease = {
                "concept_id": concept_id,
                "label": label,
                "aliases": aliases,
                "xrefs": xrefs,
                "associated_with": associated_with
            }
            self._load_disease(disease)
