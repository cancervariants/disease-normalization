"""A base class for extraction, transformation, and loading of data."""
from abc import ABC, abstractmethod
from disease.database import Database
from disease.schemas import Disease
import owlready2 as owl
from typing import Set, Dict, List
import logging

logger = logging.getLogger('disease')
logger.setLevel(logging.DEBUG)


class Base(ABC):
    """The ETL base class."""

    def __init__(self, database: Database):
        """Extract from sources."""
        self.database = database

    @abstractmethod
    def perform_etl(self) -> List:
        """Public-facing method to begin ETL procedures on given data.

        :return: List of concept IDs to be added to merge generation.
        """
        raise NotImplementedError

    def _extract_data(self):
        """Get source file from data directory."""
        self._data_path.mkdir(exist_ok=True, parents=True)
        src_name = type(self).__name__.lower()
        dir_files = [f for f in self._data_path.iterdir()
                     if f.name.startswith(src_name)]
        if len(dir_files) == 0:
            self._download_data()
            dir_files = list(self._data_path.iterdir())
        self._data_file = sorted(dir_files, reverse=True)[0]
        self._version = self._data_file.stem.split('_', 1)[1]

    @abstractmethod
    def _transform_data(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _load_meta(self, *args, **kwargs):
        raise NotImplementedError

    def _load_disease(self, disease: Dict):
        """Load individual disease record."""
        assert Disease(**disease)
        concept_id = disease['concept_id']

        if 'aliases' in disease:
            aliases = disease['aliases']
            if aliases == [] or aliases is None:
                del disease['aliases']
            else:
                aliases_lower = {a.lower() for a in aliases}
                if len(aliases_lower) > 20:
                    logger.debug(f"{concept_id} has > 20 aliases")
                    del disease['aliases']
                else:
                    for al in aliases_lower:
                        self.database.add_ref_record(al, concept_id, 'alias')

        for field in ('other_identifiers', 'xrefs', 'pediatric_disease'):
            if field in disease and (disease[field] is None or  # noqa: W504
                                     disease[field] is []):
                del disease[field]

        self.database.add_record(disease)
        self.database.add_ref_record(disease['label'], concept_id, 'label')
        if self._store_ids:
            self._processed_ids.append(concept_id)


class OWLBase(Base):
    """Base class for sources that use OWL files."""

    def _get_subclasses(self, uri: str) -> Set[str]:
        """Retrieve URIs for all terms that are subclasses of given URI.

        :param str uri: URI for class
        :return: Set of URIs (strings) for all subclasses of `uri`
        """
        graph = owl.default_world.as_rdflib_graph()
        query = f"""
            SELECT ?c WHERE {{
                ?c rdfs:subClassOf* <{uri}>
            }}
            """
        return {item.c.toPython() for item in graph.query(query)}

    def _get_by_property_value(self, prop: str,
                               value: str) -> Set[str]:
        """Get all classes with given value for a specific property.

        :param str prop: property URI
        :param str value: property value
        :return: Set of URIs (as strings) matching given property/value
        """
        graph = owl.default_world.as_rdflib_graph()
        query = f"""
            SELECT ?c WHERE {{
                ?c <{prop}>
                "{value}"
            }}
            """
        return {item.c.toPython() for item in graph.query(query)}
