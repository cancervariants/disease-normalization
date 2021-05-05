"""Module to load disease data from OncoTree."""
import logging
from .base import Base
from disease import PROJECT_ROOT
from disease.schemas import SourceMeta, SourceName, NamespacePrefix, Disease
from disease.database import Database
from pathlib import Path
from typing import List
import requests
import json

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class OncoTree(Base):
    """Gather and load data from OncoTree."""

    def __init__(self,
                 database: Database,
                 src_api_root: str = "http://oncotree.mskcc.org/api/",
                 data_path: Path = PROJECT_ROOT / 'data' / 'oncotree'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_api_root: root of OncoTree API URL
        :param pathlib.Path data_path: path to local OncoTree data directory
        """
        self._SRC_API_ROOT = src_api_root
        super().__init__(database=database, data_path=data_path)

    def perform_etl(self) -> List[str]:
        """Public-facing method to initiate ETL procedures on given data.

        :return: empty list (because OncoTree IDs shouldn't be used to
            construct merged concept groups)
        """
        self._extract_data()
        self._load_meta()
        self._transform_data()
        self.database.flush_batch()
        return []

    def _download_data(self):
        """Download Oncotree source data for loading into normalizer."""
        logger.info('Downloading OncoTree...')
        # get version for latest stable release
        versions_url = f"{self._SRC_API_ROOT}versions"
        versions = json.loads(requests.get(versions_url).text)
        latest = [v['release_date'] for v in versions
                  if v['api_identifier'] == 'oncotree_latest_stable'][0]
        version = latest.replace('-', '_')

        # download data
        url = f'{self._SRC_API_ROOT}tumorTypes/tree?version=oncotree_{version}'
        try:
            response = requests.get(url, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'OncoTree download failed: {e}')
            raise e
        filename = self._data_path / f'oncotree_{version}.json'
        handle = open(filename, 'wb')
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        self._version = version
        logger.info('Finished downloading OncoTree')

    def _load_meta(self):
        """Load metadata"""
        metadata = SourceMeta(data_license="CC BY 4.0",
                              data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
                              version=self._version,
                              data_url="http://oncotree.mskcc.org/#/home?tab=api",  # noqa: E501
                              rdp_url=None,
                              data_license_attributes={
                                  'non_commercial': False,
                                  'share_alike': False,
                                  'attribution': True
                              })
        params = dict(metadata)
        params['src_name'] = SourceName.ONCOTREE.value
        self.database.metadata.put_item(Item=params)

    def _traverse_tree(self, disease_node):
        """Traverse JSON tree and load diseases where possible.

        :param Dict disease_node: node in tree containing info for individual
            disease.
        """
        if disease_node.get('level', None) >= 2:
            disease = {
                "concept_id": f"{NamespacePrefix.ONCOTREE.value}:{disease_node['code']}",  # noqa: E501
                "label": disease_node['name'],
                "xrefs": [],
                "associated_with": [],
            }
            refs = disease_node.get('externalReferences', [])
            for prefix, codes in refs.items():
                if prefix == 'UMLS':
                    normed_prefix = NamespacePrefix.UMLS.value
                    for code in codes:
                        normed_id = f"{normed_prefix}:{code}"
                        disease['associated_with'].append(normed_id)
                elif prefix == 'NCI':
                    normed_prefix = NamespacePrefix.NCIT.value
                    for code in codes:
                        normed_id = f"{normed_prefix}:{code}"
                        disease['xrefs'].append(normed_id)
                else:
                    logger.warning(f"Unrecognized prefix: {prefix}")
                    continue
            assert Disease(**disease)
            self._load_disease(disease)
        if disease_node.get('children', None):
            for child in disease_node['children'].values():
                self._traverse_tree(child)

    def _transform_data(self):
        """Initiate OncoTree data transformation."""
        with open(self._data_file, 'r') as f:
            oncotree = json.load(f)
        self._traverse_tree(oncotree['TISSUE'])
