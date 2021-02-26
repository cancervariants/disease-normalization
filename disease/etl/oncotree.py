"""Module to load disease data from OncoTree."""
import logging
from .base import Base
from disease import PROJECT_ROOT
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
        self.database = database
        self._SRC_API_ROOT = src_api_root
        self._data_path = data_path

    def perform_etl(self) -> List[str]:
        """Public-facing method to initiate ETL procedures on given data.

        :return: empty set (because OncoTree IDs shouldn't be used to construct
            merged concept groups)
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
        versions_url = self._SRC_API_ROOT + 'versions'
        versions = json.loads(requests.get(versions_url).text)
        latest = [v['release_date'] for v in versions
                  if v['api_identifier'] == 'oncotree_latest_stable'][0]
        version = latest.replace('-', '_')

        # download data
        url = f'{self._SRC_API_ROOT}tumor_types.txt?version=oncotree_{version}'
        try:
            response = requests.get(url, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'OncoTree download failed: {e}')
            raise e
        filename = self._data_path / f'oncotree_{version}.txt'
        handle = open(filename, 'wb')
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        self._version = version
        logger.info('Finished downloading OncoTree')
