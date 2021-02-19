"""Module to load disease data from Mondo Disease Ontology."""
from .base import OWLBase
import logging
from disease import PROJECT_ROOT, PREFIX_LOOKUP
from disease.database import Database
from disease.schemas import Meta, SourceName, NamespacePrefix, Disease
from pathlib import Path
import requests
import owlready2 as owl
from typing import Dict


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


MONDO_PREFIX_LOOKUP = {
    "NCIT": NamespacePrefix.NCIT,
    "DOID": NamespacePrefix.DO,
    "OGMS": NamespacePrefix.OGMS,
    "Orphanet": NamespacePrefix.ORPHANET,
    "MESH": NamespacePrefix.MESH,
    "EFO": NamespacePrefix.EFO,
    "UMLS": NamespacePrefix.UMLS,
    "UMLS_CUI": NamespacePrefix.UMLS,
    "ICD9": NamespacePrefix.ICD9,
    "ICD9CM": NamespacePrefix.ICD9CM,
    "ICD10": NamespacePrefix.ICD10,
    "ICD10CM": NamespacePrefix.ICD10CM,
    "ICDO": NamespacePrefix.ICDO,
    "IDO": NamespacePrefix.IDO,
    "GARD": NamespacePrefix.GARD,
    "OMIM": NamespacePrefix.OMIM,
    "OMIMPS": NamespacePrefix.OMIMPS,
    "KEGG": NamespacePrefix.KEGG,
    "COHD": NamespacePrefix.COHD,
    "HPO": NamespacePrefix.HPO,
    "NIFSTD": NamespacePrefix.NIFSTD,
    "MF": NamespacePrefix.MF,
    "HP": NamespacePrefix.HPO,
    "MedDRA": NamespacePrefix.MEDDRA,
    "MEDDRA": NamespacePrefix.MEDDRA,
    "ONCOTREE": NamespacePrefix.ONCOTREE,
    "Wikipedia": NamespacePrefix.WIKIPEDIA,
    "Wikidata": NamespacePrefix.WIKIDATA,
    "MEDGEN": NamespacePrefix.MEDGEN,
    "MP": NamespacePrefix.MP,
    "PATO": NamespacePrefix.PATO,
}


class Mondo(OWLBase):
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
        :param pathlib.Path data_path: path to local Mondo data directory
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
        """Download Mondo thesaurus source file for loading into normalizer."""
        logger.info('Downloading Mondo data...')
        try:
            response = requests.get(self._SRC_URL, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'Mondo download failed: {e}')
            raise e
        handle = open(self._data_path / f'mondo_{self._version}.owl', "wb")
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

    def _transform_data(self):
        """Gather and transform disease entities."""
        mondo = owl.get_ontology(self._data_file.absolute().as_uri())
        mondo.load()

        # gather constants/search materials
        disease_root = "http://purl.obolibrary.org/obo/MONDO_0000001"
        disease_uris = self._get_subclasses(disease_root)
        peds_neoplasm_root = "http://purl.obolibrary.org/obo/MONDO_0006517"
        peds_uris = self._get_subclasses(peds_neoplasm_root)
        adult_onset_pattern = 'http://purl.obolibrary.org/obo/mondo/patterns/adult.yaml'  # noqa: E501

        for uri in disease_uris:
            try:
                disease = mondo.search(iri=uri)[0]
            except TypeError:
                logger.error(f"Could not retrieve class for URI {uri}")
                continue
            try:
                label = disease.label[0]
            except IndexError:
                logger.debug(f"No label for concept {uri}")
                continue

            params = {
                'concept_id': disease.id[0].lower(),
                'label': label,
                'aliases': list({d for d in disease.hasExactSynonym if d != label}),  # noqa: E501
                'xrefs': [],
                'other_identifiers': []
            }

            for ref in disease.hasDbXref:
                prefix, id_no = ref.split(':', 1)
                normed_prefix = MONDO_PREFIX_LOOKUP.get(prefix, None)
                if not normed_prefix:
                    continue
                other_id = f'{normed_prefix.value}:{id_no}'

                if normed_prefix.value in PREFIX_LOOKUP:
                    params['other_identifiers'].append(other_id)
                elif normed_prefix == NamespacePrefix.KEGG:
                    other_id = f'{normed_prefix.value}:H{id_no}'
                    params['xrefs'].append(other_id)
                else:
                    params['xrefs'].append(other_id)

            if disease.iri in peds_uris:
                params['pediatric'] = True
            else:
                conforms_to = disease.conformsTo
                if conforms_to and adult_onset_pattern in conforms_to:
                    params['pediatric'] = False

            assert Disease(**params)  # check input validity
            self._load_disease(params)

    def _load_disease(self, disease: Dict):
        """Load individual disease and associated references.

        :param Dict disease: individual disease record to be loaded
        """
        concept_id = disease['concept_id']
        aliases = disease['aliases']
        if aliases:
            if len({a.casefold() for a in aliases}) > 20:
                logger.debug(f'{concept_id} has > 20 aliases')
                del disease['aliases']
            else:
                for alias in aliases:
                    self.database.add_ref_record(alias, concept_id, 'alias')
        else:
            del disease['aliases']
        for key in ('xrefs', 'other_identifiers'):
            if not disease[key]:
                del disease[key]

        self.database.add_record(disease)
        self.database.add_ref_record(disease['label'], concept_id, 'label')
