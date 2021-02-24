"""A base class for extraction, transformation, and loading of data."""
from abc import ABC, abstractmethod
from disease.database import Database
import owlready2 as owl
from typing import Set


class Base(ABC):
    """The ETL base class."""

    def __init__(self, database: Database):
        """Extract from sources."""
        self.database = database

    @abstractmethod
    def perform_etl(self):
        """Public-facing method to begin ETL procedures on given data."""
        raise NotImplementedError

    @abstractmethod
    def _extract_data(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _transform_data(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _load_meta(self, *args, **kwargs):
        raise NotImplementedError


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
