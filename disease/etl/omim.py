"""Module to load disease data from OMIM."""
import logging
from .base import Base
from disease import PROJECT_ROOT, DownloadException
from disease.schemas import Meta, SourceName, Disease, NamespacePrefix
from disease.database import Database
from pathlib import Path
from typing import List

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class OMIM(Base):
    """Gather and load data from OMIM.

    MIM number prefix:
    ------------------
    Asterisk (*)  Gene (exclude)
    Plus (+)  Gene and phenotype, combined  (exclude)
    Number Sign (#)  Phenotype, molecular basis known
    Percent (%)  Phenotype or locus, molecular basis unknown
    NULL (<null>)  Other, mainly phenotypes with suspected mendelian basis
    Caret (^)  Entry has been removed from the database or moved to another
    entry (exclude)
    """

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

    def _transform_data(self):
        """Modulate data and prepare for loading."""
        with open(self._data_file, 'r') as f:
            rows = f.readlines()
        rows = [r.rstrip() for r in rows if not r.startswith('#')]
        rows = [[g for g in r.split('\t')] for r in rows]
        rows = [r for r in rows if r[0] not in ('Asterisk', 'Caret', 'Plus')]
        for row in rows:
            disease = {
                'concept_id': f'{NamespacePrefix.OMIM.value}:row[1]',
                'aliases': []
            }
            aliases = {}

            label_item = row[2]
            if ';' in label_item:
                label_split = label_item.split(';')
                disease['label'] = label_split[0]
                aliases.add(label_split[1])
            else:
                disease['label'] = row[2]

            if len(row) > 3:
                aliases |= {title for title in row[3].split(';') if title}
            if len(row) > 4:
                aliases |= {title for title in row[4].split(';') if title}
            aliases = {alias[:-10] if alias.endswith(', INCLUDED') else alias
                       for alias in aliases}
            disease['aliases'] = list(aliases)

            assert Disease(**disease)
            self._load_disease(disease)