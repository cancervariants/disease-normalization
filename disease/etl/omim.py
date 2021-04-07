"""Module to load disease data from OMIM."""
import logging
from .base import Base
from disease import PROJECT_ROOT, DownloadException
from disease.schemas import SourceMeta, SourceName, Disease, NamespacePrefix
from disease.database import Database
from pathlib import Path
from typing import List

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class OMIM(Base):
    """Gather and load data from OMIM."""

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
            raise DownloadException(f"Could not access OMIM data - see README "
                                    f"for details. Input data must be "
                                    f"manually placed in "
                                    f"{self._data_path.absolute().as_uri()}")
        self._load_meta()
        self._transform_data()
        self.database.flush_batch()
        return []

    def _download_data(self):
        """Download OMIM source data for loading into normalizer."""
        raise DownloadException("OMIM data not available for public download")

    def _load_meta(self):
        """Load source metadata."""
        metadata = SourceMeta(data_license="custom",
                              data_license_url="https://omim.org/help/agreement",  # noqa: E501
                              version=self._data_file.stem.split('_', 1)[1],
                              data_url=self._SRC_URL,
                              rdp_url='http://reusabledata.org/omim.html',
                              data_license_attributes={
                                  'non_commercial': False,
                                  'share_alike': True,
                                  'attribution': True
                              })
        params = dict(metadata)
        params['src_name'] = SourceName.OMIM.value
        self.database.metadata.put_item(Item=params)

    def _transform_data(self):
        """Modulate data and prepare for loading."""
        with open(self._data_file, 'r') as f:
            rows = f.readlines()
        rows = [r.rstrip() for r in rows if not r.startswith('#')]
        rows = [[g for g in r.split('\t')] for r in rows]
        rows = [r for r in rows if r[0] not in ('Asterisk', 'Caret', 'Plus')]
        for row in rows:
            disease = {
                'concept_id': f'{NamespacePrefix.OMIM.value}:{row[1]}',
            }
            aliases = set()

            label_item = row[2]
            if ';' in label_item:
                label_split = label_item.split(';')
                disease['label'] = label_split[0]
                aliases.add(label_split[1])
            else:
                disease['label'] = row[2]

            if len(row) > 3:
                aliases |= {t for t in row[3].split(';') if t}
            if len(row) > 4:
                aliases |= {t for t in row[4].split(';') if t}
            aliases = {alias[:-10] if alias.endswith(', INCLUDED') else alias
                       for alias in aliases}
            disease['aliases'] = [a.lstrip() for a in aliases]

            assert Disease(**disease)
            self._load_disease(disease)
