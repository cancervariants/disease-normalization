"""Module to load disease data from NCIt."""
import logging
from .base import OWLBase
from disease import PROJECT_ROOT
from disease.database import Database
from disease.schemas import Meta, SourceName, NamespacePrefix, Disease
from pathlib import Path
import requests
import zipfile
from os import remove, rename
from typing import Set, Dict
import owlready2 as owl
from owlready2.entity import ThingClass
import re


logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)

icdo_re = re.compile("[0-9]+/[0-9]+")


class NCIt(OWLBase):
    """Gather and load data from NCIt."""

    def __init__(self,
                 database: Database,
                 src_dir: str = "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/archive/21.01d_Release/",  # noqa F401
                 src_fname: str = "Thesaurus_21.01d.OWL.zip",
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
        try:
            response = requests.get(url, stream=True)
        except requests.exceptions.RequestException as e:
            logger.error(f'NCIt download failed: {e}')
            raise e
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
        dir_files = [f for f in self._data_path.iterdir()
                     if f.name.startswith('ncit')]
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files, reverse=True)[0]
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

    def _get_disease_classes(self) -> Set[ThingClass]:
        """Get all nodes with semantic_type 'Neoplastic Process' or 'Disease
        or Syndrome'.

        :return: uq_nodes with additions from above types added
        :rtype: Set[owlready2.entity.ThingClass]
        """
        p106 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        neopl = self._get_by_property_value(p106, "Neoplastic Process")
        dos = self._get_by_property_value(p106, "Disease or Syndrome")
        p310 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        retired = self._get_by_property_value(p310, "Retired_Concept")
        uris = neopl.union(dos) - retired
        return uris

    def _transform_data(self):
        """Get data from file and construct object for loading."""
        ncit = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        disease_uris = self._get_disease_classes()
        for uri in disease_uris:
            disease_class = ncit.search(iri=uri)[0]
            concept_id = f"{NamespacePrefix.NCIT.value}:{disease_class.name}"
            if disease_class.P108:
                label = disease_class.P108.first()
            else:
                logger.warning(f"No label for concept {concept_id}")
                continue
            aliases = disease_class.P90
            if aliases and label in aliases:
                aliases.remove(label)

            xrefs = []
            if disease_class.P207:
                xrefs.append(f"{NamespacePrefix.UMLS.value}:"
                             f"{disease_class.P207.first()}")
            maps_to = disease_class.P375
            if maps_to:
                icdo_list = list(filter(lambda s: icdo_re.match(s), maps_to))
                if len(icdo_list) == 1:
                    xrefs.append(f"{NamespacePrefix.ICDO.value}:"
                                 f"{icdo_list[0]}")
            imdrf = disease_class.hasDbXref
            if imdrf:
                xrefs.append(f"{NamespacePrefix.IMDRF.value}:"
                             f"{imdrf[0].split(':')[1]}")

            disease = {
                'concept_id': concept_id,
                'src_name': SourceName.NCIT.value,
                'label': label,
                'aliases': aliases,
                'xrefs': xrefs
            }
            assert Disease(**disease)
            self._load_disease(disease)

    def _load_disease(self, disease: Dict):
        """Load individual disease record along with reference items.

        :param Dict disease: disease record to load
        """
        aliases = disease['aliases']
        concept_id = disease['concept_id']
        if len({a.casefold() for a in aliases}) > 20:
            logger.debug(f'{concept_id} has > 20 aliases')
            del disease['aliases']
        elif not aliases:
            del disease['aliases']
        else:
            disease['aliases'] = list(set(aliases))
            case_uq_aliases = {a.lower() for a in disease['aliases']}
            for alias in case_uq_aliases:
                self.database.add_ref_record(alias, concept_id, 'alias')
        self.database.add_ref_record(disease['label'], concept_id, 'label')
        self.database.add_record(disease)
