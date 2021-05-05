"""Disease Ontology ETL module."""
import logging
from .base import OWLBase
import requests
from pathlib import Path
from disease import PROJECT_ROOT, PREFIX_LOOKUP
from disease.schemas import SourceMeta, SourceName, NamespacePrefix
from disease.database import Database
from datetime import datetime
import owlready2 as owl
from typing import List


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)

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

    def __init__(self,
                 database: Database,
                 src_dload_page: str = "http://www.obofoundry.org/ontology/doid.html",  # noqa: E501
                 src_url: str = "http://purl.obolibrary.org/obo/doid/doid-merged.owl",  # noqa: E501
                 data_path: Path = PROJECT_ROOT / 'data' / 'do'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_dload_page: URL for source data download webpage
        :param str src_url: URL for source data file
        :param pathlib.Path data_path: path to local DO data directory
        """
        self._SRC_DLOAD_PAGE = src_dload_page
        self._SRC_URL = src_url
        self._version = datetime.strftime(datetime.now(), "%Y%m%d")
        super().__init__(database=database, data_path=data_path)

    def perform_etl(self) -> List[str]:
        """Public-facing method to initiate ETL procedures on given data.

        :return: empty list (because DO IDs shouldn't be used to construct
            merged concept groups)
        """
        self._extract_data()
        self._load_meta()
        self._transform_data()
        self.database.flush_batch()
        return []

    def _download_data(self):
        """Download DO source file for loading into normalizer."""
        logger.info('Downloading DO data...')
        try:
            response = requests.get(self._SRC_URL, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'DO download failed: {e}')
            raise e
        handle = open(self._data_path / f'do_{self._version}.owl', "wb")
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        logger.info('Finished downloading Human Disease Ontology')

    def _load_meta(self):
        """Load metadata"""
        metadata_params = {
            "data_license": "CC0 1.0",
            "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",  # noqa: E501
            "version": self._version,
            "data_url": self._SRC_DLOAD_PAGE,
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
        diseases = self._get_subclasses(disease_uri)
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
