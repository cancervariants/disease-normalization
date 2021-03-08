"""Module to load disease data from OMIM."""
import logging
from .base import Base
from disease import PROJECT_ROOT, DownloadException
from disease.schemas import Meta, SourceName
from disease.database import Database
from pathlib import Path
from typing import List

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class OMIM(Base):
    """Gather and load data from OncoTree."""

    def __init__(self,
                 database: Database,
                 src_url: str = "https://www.omim.org/downloads",
                 data_path: Path = PROJECT_ROOT / 'data' / 'omim'):
        """Override base class init method.

        :param therapy.database.Database database: app database instance
        :param pathlib.Path data_path: path to local OMIM data directory
        """
        self._SRC_URL = src_url
        super().__init__(database=database, data_path=data_path)

    def perform_etl(self) -> List[str]:
        """Public-facing method to initiate ETL procedures on given data.

        :return: empty list (because OMIM IDs shouldn't be used to construct
            merged concept groups)
        """
        try:
            self._extract_data()
        except DownloadException:
            logger.error("OMIM data extraction failed: input file must be "
                         "manually placed in data directory.")
        self._load_meta()
        self._transform_data()
        self.database.flush_batch()
        return []

    def _download_data(self):
        """Download OMIM source data for loading into normalizer."""
        raise DownloadException("OMIM data not available for public download")

    def _load_meta(self):
        """Load source metadata."""
        metadata = Meta(data_license="CC BY 4.0",
                        data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
                        version=self._data_file.stem.split('_', 1)[1],
                        data_url=self._SRC_URL,
                        rdp_url='http://reusabledata.org/omim.html',
                        data_license_attributes={
                            'non_commercial': False,  # TODO double-check
                            'share_alike': True,
                            'attribution': True
                        })
        params = dict(metadata)
        params['src_name'] = SourceName.OMIM.value
        self.database.metadata.put_item(Item=params)
