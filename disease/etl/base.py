"""A base class for extraction, transformation, and loading of data."""
from abc import ABC, abstractmethod
from therapy.database import Database


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
