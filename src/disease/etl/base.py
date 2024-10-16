"""Provides abstract base classes for source ETL procedures.

Generally, users shouldn't ever have to work directly with the classes contained within.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import click
from owlready2.rdflib_store import TripleLiteRDFlibGraph as RDFGraph
from wags_tails import CustomData, DataSource, DoData, MondoData, NcitData, OncoTreeData

from disease import ITEM_TYPES, SOURCES_FOR_MERGE
from disease.database import AbstractDatabase
from disease.schemas import Disease, SourceName

DATA_DISPATCH = {
    SourceName.NCIT: NcitData,
    SourceName.ONCOTREE: OncoTreeData,
    SourceName.MONDO: MondoData,
    SourceName.DO: DoData,
}

_logger = logging.getLogger(__name__)


class Base(ABC):
    """The ETL base class."""

    def __init__(
        self,
        database: AbstractDatabase,
        data_path: Path | None = None,
        silent: bool = True,
    ) -> None:
        """Extract from sources.

        :param database: database client
        :param data_path: location of data directory
        :param silent: if True, don't print ETL results to console
        """
        self._silent = silent
        self._src_name = SourceName(self.__class__.__name__)
        self._data_source: NcitData | OncoTreeData | MondoData | DoData | CustomData = (
            self._get_data_handler(data_path)
        )
        self._database = database
        self._store_ids = self.__class__.__name__ in SOURCES_FOR_MERGE
        if self._store_ids:
            self._added_ids = []

    def _get_data_handler(self, data_path: Path | None = None) -> DataSource:
        """Construct data handler instance for source. Overwrite for edge-case sources.

        :param data_path: location of data storage
        :return: instance of wags_tails.DataSource to manage source file(s)
        """
        return DATA_DISPATCH[self._src_name](data_dir=data_path, silent=self._silent)

    def perform_etl(self, use_existing: bool = False) -> list:
        """Public-facing method to begin ETL procedures on given data.

        :param use_existing: if True, use local data instead of retrieving most recent
            version
        :return: List of concept IDs to be added to merge generation.
        """
        self._extract_data(use_existing)
        self._load_meta()
        if not self._silent:
            click.echo("Transforming and loading data to DB...")
        self._transform_data()
        self._database.complete_write_transaction()
        if self._store_ids:
            return self._added_ids
        return []

    def _extract_data(self, use_existing: bool = False) -> None:
        """Get source file from data directory.
        :param use_existing: if True, use local data regardless of whether it's up to
            date
        """
        self._data_file, self._version = self._data_source.get_latest(
            from_local=use_existing
        )

    @abstractmethod
    def _transform_data(self, *args, **kwargs) -> None:  # noqa: ANN002
        raise NotImplementedError

    @abstractmethod
    def _load_meta(self, *args, **kwargs) -> None:  # noqa: ANN002
        raise NotImplementedError

    def _load_disease(self, disease: dict) -> None:
        """Load individual disease record."""
        _ = Disease(**disease)
        concept_id = disease["concept_id"]

        for attr_type in ITEM_TYPES:
            if attr_type in disease:
                value = disease[attr_type]
                if value is not None and value != []:
                    if isinstance(value, str):
                        items = [value.lower()]
                    else:
                        disease[attr_type] = list(set(value))
                        items = {item.lower() for item in value}
                        if (attr_type == "aliases") and (len(items) > 20):
                            _logger.debug("%s has > 20 aliases.", concept_id)
                            del disease[attr_type]
                            continue

                else:
                    del disease[attr_type]

        for field in ("pediatric_disease", "oncologic_disease"):
            if field in disease and disease[field] is None:
                del disease[field]

        self._database.add_record(disease, self._src_name)
        if self._store_ids:
            self._added_ids.append(concept_id)


class OWLBase(Base):
    """Base class for sources that use OWL files."""

    def _get_subclasses(self, uri: str, graph: RDFGraph) -> set[str]:
        """Retrieve URIs for all terms that are subclasses of given URI.

        :param uri: URI for class
        :param graph: RDFLib graph of ontology default world
        :return: Set of URIs (strings) for all subclasses of `uri`
        """
        query = f"""
            SELECT ?c WHERE {{
                ?c rdfs:subClassOf* <{uri}>
            }}
            """
        return {item.c.toPython() for item in graph.query(query)}

    def _get_by_property_value(
        self, prop: str, value: str, graph: RDFGraph
    ) -> set[str]:
        """Get all classes with given value for a specific property.

        :param prop: property URI
        :param value: property value
        :param graph: RDFLib graph of ontology default world
        :return: Set of URIs (as strings) matching given property/value
        """
        query = f"""
            SELECT ?c WHERE {{
                ?c <{prop}>
                "{value}"
            }}
            """
        return {item.c.toPython() for item in graph.query(query)}
