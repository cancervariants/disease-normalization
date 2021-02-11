"""Module to load disease data from NCIt."""
import logging
from .base import Base
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

    def _get_typed_nodes(self, uq_nodes: Set[ThingClass],
                         ncit: owl.namespace.Ontology) -> Set[ThingClass]:
        """Get all nodes with semantic_type Neoplastic Process

        :param Set[owlready2.entity.ThingClass] uq_nodes: set of unique class
            nodes found so far.
        :param owl.namespace.Ontology ncit: owlready2 Ontology instance for
            NCI Thesaurus.
        :return: uq_nodes, with the addition of all classes found to have
            semantic_type Pharmacologic Substance and not of type
            Retired_Concept
        :rtype: Set[owlready2.entity.ThingClass]
        """
        graph = owl.default_world.as_rdflib_graph()

        query_str = '''SELECT ?x WHERE {
            ?x <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106>
            "Neoplastic Process"
        }'''
        typed_results = set(graph.query(query_str))

        retired_query_str = '''SELECT ?x WHERE {
            ?x <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P310>
            "Retired_Concept"
        }
        '''
        retired_results = set(graph.query(retired_query_str))

        typed_results = typed_results - retired_results

        for result in typed_results:
            # parse result as URI and get ThingClass object back from NCIt
            class_object = ncit[result[0].toPython().split('#')[1]]
            uq_nodes.add(class_object)
        return uq_nodes

    def _transform_data(self):
        """Get data from file and construct object for loading."""
        ncit = owl.get_ontology(self._data_file.absolute().as_uri())
        ncit.load()
        uq_nodes = set()
        uq_nodes = self._get_typed_nodes(uq_nodes, ncit)

        for node in uq_nodes:
            concept_id = f"{NamespacePrefix.NCIT.value}:{node.name}"
            if node.P108:
                label = node.P108.first()
            else:
                logger.warning(f"No label for concept {concept_id}")
                continue
            aliases = node.P90
            if aliases and label in aliases:
                aliases.remove(label)

            xrefs = []
            if node.P207:
                xrefs.append(f"{NamespacePrefix.UMLS.value}:"
                             f"{node.P207.first()}")

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
        elif not disease['aliases']:
            del disease['aliases']
        else:
            disease['aliases'] = list(set(aliases))
            case_uq_aliases = {a.lower() for a in disease['aliases']}
            for alias in case_uq_aliases:
                self.database.add_ref_record(alias, concept_id, 'alias')
        self.database.add_ref_record(disease['label'], concept_id, 'label')
        self.database.add_record(disease)
