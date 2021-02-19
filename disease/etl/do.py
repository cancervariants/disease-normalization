"""Disease Ontology ETL module."""
import logging
from .base import Base
from pathlib import Path
from disease import PROJECT_ROOT
from disease.schemas import Meta, SourceName
from disease.database import Database
import requests
from datetime import datetime


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class DO(Base):
    """Disease Ontology ETL class."""

    def __init__(self,
                 database: Database,
                 src_url: str = "http://purl.obolibrary.org/obo/doid.owl",
                 data_path: Path = PROJECT_ROOT / 'data' / 'do'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param str src_url: URL for source data OWL file
        :param pathlib.Path data_path: path to local DO data directory
        """
        self.database = database
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
        dir_files = list(self._data_path.iterdir())
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files)[-1]
        self._version = self._data_file.stem.split('_')[1]

    def _load_meta(self):
        """Load metadata"""
        metadata_params = {
            "data_license": "CC0 1.0",
            "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",  # noqa: E501
            "version": self._version,
            "data_url": self._SRC_URL,
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
