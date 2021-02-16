"""Module to load disease data from Mondo."""
import logging
from .base import Base
from disease import PROJECT_ROOT
from disease.database import Database
from disease.schemas import Meta, SourceName, NamespacePrefix, Disease
from pathlib import Path
import requests
from typing import Set
import owlready2 as owl
from owlready2.entity import ThingClass
from rdflib.term import URIRef


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


MONDO_PREFIX_LOOKUP = {
    "NCIT": NamespacePrefix.NCIT,
    "DOID": NamespacePrefix.DO,
    "SCTID": NamespacePrefix.SNOMEDCT,
    "ICD9": NamespacePrefix.ICD9,
    "OGMS": NamespacePrefix.OGMS,
    "MESH": NamespacePrefix.MESH,
    "EFO": NamespacePrefix.EFO,
    "UMLS": NamespacePrefix.UMLS,
    "ICD10": NamespacePrefix.ICD10,
    "IDO": NamespacePrefix.IDO,
    "GARD": NamespacePrefix.GARD,
    "OMIM": NamespacePrefix.OMIM,
    "OMIMPS": NamespacePrefix.OMIMPS,
    "KEGG": NamespacePrefix.KEGG,  # also need to +'H' to ID
    "COHD": NamespacePrefix.COHD,
    "HPO": NamespacePrefix.HPO,
    "NIFSTD": NamespacePrefix.NIFSTD,
    "MF": NamespacePrefix.MF,
    "ICDO": NamespacePrefix.ICDO,
}


class Mondo(Base):
    """Gather and load data from Mondo."""

    def __init__(self,
                 database: Database,
                 src_dload_page: str = "https://mondo.monarchinitiative.org/pages/download/",  # noqa F401
                 src_url: str = "http://purl.obolibrary.org/obo/mondo.owl",
                 version: str = "20210129",
                 data_path: Path = PROJECT_ROOT / 'data' / 'mondo'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_dload_page: user-facing download page
        :param str src_url: direct URL to OWL file download
        :param pathlib.Path data_path: path to local NCIt data directory
        """
        self.database = database
        self._SRC_DLOAD_PAGE = src_dload_page
        self._SRC_URL = src_url
        self._version = version
        self._data_path = data_path

    def perform_etl(self):
        """Public-facing method to initiate ETL procedures on given data."""
        self._extract_data()
        self._load_meta()
        self._transform_data()

    def _download_data(self):
        """Download NCI thesaurus source file for loading into normalizer."""
        logger.info('Downloading NCI Thesaurus...')
        try:
            response = requests.get(self._SRC_URL, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'MONDO download failed: {e}')
            raise e
        handle = open(self._data_path / f'mondo_{self.version}.owl', "wb")
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        logger.info('Finished downloading Mondo Disease Ontology')

    def _extract_data(self):
        """Get Mondo source file."""
        self._data_path.mkdir(exist_ok=True, parents=True)
        dir_files = list(self._data_path.iterdir())
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files)[-1]

    def _load_meta(self):
        """Load metadata"""
        metadata = Meta(data_license="CC BY 4.0",
                        data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
                        version=self._version,
                        data_url=self._SRC_DLOAD_PAGE,
                        rdp_url='http://reusabledata.org/monarch.html',
                        data_license_attributes={
                            'non_commercial': False,
                            'share_alike': False,
                            'attribution': True
                        })
        params = dict(metadata)
        params['src_name'] = SourceName.MONDO.value
        self.database.metadata.put_item(Item=params)

    def _collect_diseases(self) -> Set[URIRef]:
        """Retrieve IRIs for all disease terms.

        :return: Set of URI references to all disease subclasses
        """
        graph = owl.default_world.as_rdflib_graph()
        disease_query = """
        SELECT ?c WHERE {
        ?c rdfs:subClassOf* <http://purl.obolibrary.org/obo/MONDO_0000001>
        }
        """
        return {item.c for item in graph.query(disease_query)}

    def _transform_data(self):
        """Gather and transform disease entities."""
        mondo = owl.get_ontology(self._data_file.absolute().as_uri())
        mondo.load()

        disease_uris = self._collect_diseases()

        for uri in disease_uris:
            disease = mondo.get(iri=uri)[0]
            self._load_disease(disease)

    def _load_disease(self, disease: ThingClass):
        """Load individual disease and associated references.

        :param ThingClass disease: individual Owl class for given disease
        """
        params = {
            'concept_id': disease.id[0].lower(),
            'label': disease.label[0],
            'aliases': list(set(disease.hasExactSynonym)),
            'xrefs': [],
            'other_identifiers': []
        }
        for ref in disease.hasDbXref:
            prefix, id_no = ref.split(':')
            normed_prefix = MONDO_PREFIX_LOOKUP[prefix]
            other_id = f'{normed_prefix.value}:{id_no}'
            if normed_prefix == NamespacePrefix.NCIT:
                params['xrefs'].append(other_id)
            if normed_prefix == NamespacePrefix.KEGG:
                other_id = f'{normed_prefix.value}:H{id_no}'
                params['other_identifiers'].append(other_id)
            else:
                params['other_identifiers'].append(other_id)
        assert Disease(**params)  # check input validity

        concept_id = params['concept_id']
        aliases = params['aliases']
        if aliases:
            for alias in aliases:
                self.database.add_ref_record(alias, concept_id, 'alias')
        else:
            del params['aliases']
        for key in ('xrefs', 'other_identifiers'):
            if not params[key]:
                del params[key]
        self.database.add_record(params)
        self.database.add_ref_record(params['label'], concept_id, 'label')
