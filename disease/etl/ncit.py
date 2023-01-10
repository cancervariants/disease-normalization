"""Module to load disease data from NCIt."""
import requests
from typing import Set
import owlready2 as owl
import re

from disease import logger
from disease.schemas import SourceMeta, SourceName, NamespacePrefix
from disease.etl.base import OWLBase
from disease.etl.utils import DownloadException


icdo_re = re.compile("[0-9]+/[0-9]+")


class NCIt(OWLBase):
    """Gather and load data from NCIt."""

    def _download_data(self) -> None:
        """Download NCI thesaurus source file.
        The NCI directory structure can be a little tricky, so this method attempts to
        retrieve a file matching the latest version number from both the subdirectory
        root (where the current version is typically posted) as well as the year-by-year
        archives if that fails.
        """
        logger.info("Retrieving source data for NCIt")
        base_url = "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus"
        # ping base NCIt directory
        release_fname = f"Thesaurus_{self._version}.OWL.zip"
        src_url = f"{base_url}/{release_fname}"
        r_try = requests.get(src_url)
        if r_try.status_code != 200:
            # ping NCIt archive directories
            archive_url = f"{base_url}/archive/{self._version}_Release/{release_fname}"
            archive_try = requests.get(archive_url)
            if archive_try.status_code != 200:
                old_archive_url = f"{base_url}/archive/20{self._version[0:2]}/{self._version}_Release/{release_fname}"  # noqa: E501
                old_archive_try = requests.get(old_archive_url)
                if old_archive_try.status_code != 200:
                    msg = (
                        f"NCIt download failed: tried {src_url}, {archive_url}, and "
                        f"{old_archive_url}"
                    )
                    logger.error(msg)
                    raise DownloadException(msg)
                else:
                    src_url = old_archive_url
            else:
                src_url = archive_url

        self._http_download(src_url, self._src_dir / f"ncit_{self._version}.owl",
                            handler=self._zip_handler)
        logger.info("Successfully retrieved source data for NCIt")

    def _load_meta(self):
        """Load metadata"""
        metadata = SourceMeta(data_license="CC BY 4.0",
                              data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",  # noqa F401
                              version=self._version,
                              data_url="https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/",
                              rdp_url='http://reusabledata.org/ncit.html',
                              data_license_attributes={
                                  'non_commercial': False,
                                  'share_alike': False,
                                  'attribution': True
                              })
        params = dict(metadata)
        params['src_name'] = SourceName.NCIT.value
        self.database.metadata.put_item(Item=params)

    def _get_disease_classes(self) -> Set[str]:
        """Get all nodes with semantic_type 'Neoplastic Process' or 'Disease
        or Syndrome'.

        :return: uq_nodes with additions from above types added
        :rtype: Set[str]
        """
        graph = owl.default_world.as_rdflib_graph()
        p106 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        neopl = self._get_by_property_value(p106, "Neoplastic Process", graph)
        dos = self._get_by_property_value(p106, "Disease or Syndrome", graph)
        p310 = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#P106"
        retired = self._get_by_property_value(p310, "Retired_Concept", graph)
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
            aliases = [a for a in disease_class.P90 if a != label]

            associated_with = []
            if disease_class.P207:
                associated_with.append(f"{NamespacePrefix.UMLS.value}:"
                                       f"{disease_class.P207.first()}")
            maps_to = disease_class.P375
            if maps_to:
                icdo_list = list(filter(lambda s: icdo_re.match(s), maps_to))
                if len(icdo_list) == 1:
                    associated_with.append(f"{NamespacePrefix.ICDO.value}:"
                                           f"{icdo_list[0]}")
            imdrf = disease_class.hasDbXref
            if imdrf:
                associated_with.append(f"{NamespacePrefix.IMDRF.value}:"
                                       f"{imdrf[0].split(':')[1]}")

            disease = {
                'concept_id': concept_id,
                'src_name': SourceName.NCIT.value,
                'label': label,
                'aliases': aliases,
                'associated_with': associated_with
            }
            self._load_disease(disease)
