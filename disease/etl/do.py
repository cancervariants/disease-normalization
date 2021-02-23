"""Disease Ontology ETL module."""
import logging
from .base import OWLBase
from pathlib import Path
from disease import PROJECT_ROOT, PREFIX_LOOKUP
from disease.schemas import Meta, SourceName, NamespacePrefix, Disease
from disease.database import Database
import requests
from datetime import datetime
import owlready2 as owl
from typing import Dict


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
                 src_url: str = "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/master/src/ontology/doid-merged.obo",  # noqa: E501
                 data_path: Path = PROJECT_ROOT / 'data' / 'do'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_url: URL for source data OWL file
        :param pathlib.Path data_path: path to local DO data directory
        """
        self.database = database
        self._SRC_DLOAD_PAGE = src_dload_page
        self._SRC_URL = src_url
        self._data_path = data_path

    def perform_etl(self):
        """Public-facing method to initiate ETL procedures on given data."""
        self._extract_data()
        self._load_meta()
        self._transform_data()

    def _download_data(self):
        """Download DO source file."""
        logger.info('Downloading Disease Ontology...')
        try:
            response = requests.get(self._SRC_URL, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'DO download failed: {e}')
            raise e
        today = datetime.strftime(datetime.today(), "%Y%m%d")
        outfile_path = self._data_path / f'do_{today}.owl'
        handle = open(outfile_path, "wb")
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        self._version = today
        logger.info('Finished downloading Disease Ontology')

    def _extract_data(self):
        """Get DO source file."""
        self._data_path.mkdir(exist_ok=True, parents=True)
        dir_files = [f for f in self._data_path.iterdir()
                     if f.name.startswith('do')]
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files, reverse=True)[0]
        self._version = self._data_file.stem.split('_')[1]

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
        assert Meta(**metadata_params)
        metadata_params['src_name'] = SourceName.DO.value
        self.database.metadata.put_item(Item=metadata_params)

    def _transform_data(self):
        """Transform source data and send to loading method."""
        do = owl.get_ontology("http://purl.obolibrary.org/obo/doid/doid-merged.owl").load()  # noqa: E501
        disease_uri = 'http://purl.obolibrary.org/obo/DOID_4'
        diseases = self._get_subclasses(disease_uri)
        for uri in diseases:
            disease_class = do.search(iri=uri)[0]
            if disease_class.deprecated:
                continue

            concept_id = f"{NamespacePrefix.DO.value}:{uri.split('_')[-1]}"

            synonyms = disease_class.hasExactSynonym
            if synonyms:
                aliases = list(set(synonyms))
            else:
                aliases = []

            other_ids = []
            xrefs = []
            db_xrefs = set(disease_class.hasDbXref)
            for other_id in db_xrefs:
                prefix, id_no = other_id.split(':', 1)
                normed_prefix = DO_PREFIX_LOOKUP.get(prefix, None)
                if normed_prefix:
                    other_id_no = f'{normed_prefix}:{id_no}'
                    if normed_prefix in PREFIX_LOOKUP:
                        other_ids.append(other_id_no)
                    else:
                        xrefs.append(other_id_no)

            disease = {
                "concept_id": concept_id,
                "label": disease_class.label[0],
                "aliases": aliases,
                "other_identifiers": other_ids,
                "xrefs": xrefs
            }
            assert Disease(**disease)
            self._load_disease(disease)

    def _load_disease(self, disease: Dict):
        """Load individual disease record along with reference items.

        :param Dict disease: disease record to load
        """
        concept_id = disease['concept_id']
        aliases = disease['aliases']
        if len({a.casefold() for a in aliases}) > 20:
            logger.debug(f'{concept_id} has > 20 aliases')
            del disease['aliases']
        elif not aliases:
            del disease['aliases']
        else:
            disease['aliases'] = list(set(aliases))
            case_uq_aliases = {a.lower() for a in disease['aliases']}
            for alias in case_uq_aliases:
                self.database.add_ref_record(alias, concept_id, 'alias')
        for key in ['other_identifiers', 'xrefs']:
            if not disease[key]:
                del disease[key]
        self.database.add_ref_record(disease['label'], concept_id,
                                     'label')
        self.database.add_record(disease)