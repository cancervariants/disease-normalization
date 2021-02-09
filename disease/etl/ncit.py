"""Module to load disease data from NCIt."""
import logging
from .base import Base
from disease import PROJECT_ROOT
from disease.database import Database
from disease.schemas import Meta, SourceName
from pathlib import Path
import requests
import zipfile
from os import remove, rename


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class NCIt(Base):
    """Gather and load data from NCIt."""

    def __init__(self,
                 database: Database,
                 src_dir: str = "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/20.09d_Release/",  # noqa F401
                 src_fname: str = "Thesaurus_20.09d.OWL.zip",
                 data_path: Path = PROJECT_ROOT / 'data' / 'ncit'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_dir: URL of remote directory containing source input
        :param str src_fname: filename for source file within source directory
        :param pathlib.Path data_path: path to local NCIt data directory
        """
        self.database = database
        self._SRC_DIR = src_dir
        self._SRC_FNAME = src_fname
        self._data_path = data_path

    def perform_etl(self):
        """Public-facing method to initiate ETL procedures on given data."""
        self._extract_data()
        self._load_meta()
        self._transform_data()

    def _download_data(self):
        """Download NCI thesaurus source file for loading into normalizer."""
        logger.info('Downloading NCI Thesaurus...')
        url = self._SRC_DIR + self._SRC_FNAME
        zip_path = self._data_path / 'ncit.zip'
        response = requests.get(url, stream=True)
        handle = open(zip_path, "wb")
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self._data_path)
        remove(zip_path)
        version = self._SRC_DIR.split('/')[-2].split('_')[0]
        rename(self._data_path / 'Thesaurus.owl', self._data_path / f'ncit_{version}.owl')  # noqa: E501
        logger.info('Finished downloading NCI Thesaurus')

    def _extract_data(self):
        """Get NCIt source file."""
        self._data_path.mkdir(exist_ok=True, parents=True)
        dir_files = list(self._data_path.iterdir())
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files)[-1]
        self._version = self._data_file.stem.split('_')[1]

    def _load_meta(self):
        """Load metadata"""
        metadata = Meta(data_license="CC BY 4.0",
                        data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
                        version=self._version,
                        data_url=self._SRC_DIR,
                        rdp_url='http://reusabledata.org/ncit.html',
                        data_license_attributes={
                            'non_commercial': False,
                            'share_alike': False,
                            'attribution': True
                        })
        params = dict(metadata)
        params['src_name'] = SourceName.NCIT.value
        self.database.metadata.put_item(Item=params)
