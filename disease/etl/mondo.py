"""Module to load disease data from Mondo Disease Ontology."""
from .base import OWLBase
import logging
from disease import PROJECT_ROOT, PREFIX_LOOKUP
from disease.database import Database
from disease.schemas import SourceMeta, SourceName, NamespacePrefix
from pathlib import Path
import requests
import owlready2 as owl
from typing import List


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


MONDO_PREFIX_LOOKUP = {
    # built-in sources
    "NCIT": NamespacePrefix.NCIT.value,
    "DOID": NamespacePrefix.DO.value,
    # external sources
    "COHD": NamespacePrefix.COHD.value,
    "EFO": NamespacePrefix.EFO.value,
    "GARD": NamespacePrefix.GARD.value,
    "HP": NamespacePrefix.HPO.value,
    "HPO": NamespacePrefix.HPO.value,
    "ICD9": NamespacePrefix.ICD9.value,
    "ICD9CM": NamespacePrefix.ICD9CM.value,
    "ICD10": NamespacePrefix.ICD10.value,
    "ICD10CM": NamespacePrefix.ICD10CM.value,
    "ICDO": NamespacePrefix.ICDO.value,
    "IDO": NamespacePrefix.IDO.value,
    "KEGG": NamespacePrefix.KEGG.value,
    "MedDRA": NamespacePrefix.MEDDRA.value,
    "MEDDRA": NamespacePrefix.MEDDRA.value,
    "MEDGEN": NamespacePrefix.MEDGEN.value,
    "MESH": NamespacePrefix.MESH.value,
    "MF": NamespacePrefix.MF.value,
    "MP": NamespacePrefix.MP.value,
    "NIFSTD": NamespacePrefix.NIFSTD.value,
    "OGMS": NamespacePrefix.OGMS.value,
    "OMIM": NamespacePrefix.OMIM.value,
    "OMIMPS": NamespacePrefix.OMIMPS.value,
    "ONCOTREE": NamespacePrefix.ONCOTREE.value,
    "Orphanet": NamespacePrefix.ORPHANET.value,
    "PATO": NamespacePrefix.PATO.value,
    "UMLS": NamespacePrefix.UMLS.value,
    "UMLS_CUI": NamespacePrefix.UMLS.value,
    "Wikidata": NamespacePrefix.WIKIDATA.value,
    "Wikipedia": NamespacePrefix.WIKIPEDIA.value,
}


class Mondo(OWLBase):
    """Gather and load data from Mondo."""

    def __init__(self,
                 database: Database,
                 src_dload_page: str = "https://mondo.monarchinitiative.org/pages/download/",  # noqa: E501
                 src_url: str = "http://purl.obolibrary.org/obo/mondo.owl",
                 version: str = "20210129",
                 data_path: Path = PROJECT_ROOT / 'data' / 'mondo'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_dload_page: user-facing download page
        :param str src_url: direct URL to OWL file download
        :param pathlib.Path data_path: path to local Mondo data directory
        """
        self._SRC_DLOAD_PAGE = src_dload_page
        self._SRC_URL = src_url
        self._version = version
        super().__init__(database=database, data_path=data_path)

    def perform_etl(self) -> List[str]:
        """Public-facing method to initiate ETL procedures on given data.

        :return: List of concept IDs that were added.
        """
        self._extract_data()
        self._load_meta()
        self._transform_data()
        self.database.flush_batch()
        return self._processed_ids

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

    def _load_meta(self):
        """Load metadata"""
        metadata = SourceMeta(data_license="CC BY 4.0",
                              data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa: E501
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
        mondo = owl.get_ontology(self._data_file.absolute().as_uri()).load()

        # gather constants/search materials
        disease_root = "http://purl.obolibrary.org/obo/MONDO_0000001"
        disease_uris = self._get_subclasses(disease_root)
        peds_neoplasm_root = "http://purl.obolibrary.org/obo/MONDO_0006517"
        peds_uris = self._get_subclasses(peds_neoplasm_root)

        for uri in disease_uris:
            try:
                disease = mondo.search(iri=uri)[0]
            except TypeError:
                logger.error(f"Mondo.transform_data could not retrieve class "
                             f"for URI {uri}")
                continue
            try:
                label = disease.label[0]
            except IndexError:
                logger.debug(f"No label for Mondo concept {uri}")
                continue

            aliases = list({d for d in disease.hasExactSynonym if d != label})
            params = {
                'concept_id': disease.id[0].lower(),
                'label': label,
                'aliases': aliases,
                'xrefs': [],
                'associated_with': [],
            }

            for ref in disease.hasDbXref:
                prefix, id_no = ref.split(':', 1)
                normed_prefix = MONDO_PREFIX_LOOKUP.get(prefix, None)
                if not normed_prefix:
                    continue
                xref = f'{normed_prefix}:{id_no}'

                if normed_prefix.lower() in PREFIX_LOOKUP:
                    params['xrefs'].append(xref)
                elif normed_prefix == NamespacePrefix.KEGG:
                    xref = f'{normed_prefix}:H{id_no}'
                    params['associated_with'].append(xref)
                else:
                    params['associated_with'].append(xref)

            if disease.iri in peds_uris:
                params['pediatric_disease'] = True

            self._load_disease(params)
