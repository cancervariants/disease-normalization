"""Module to load and init namespace at package level."""

from .do import DO
from .merge import Merge
from .mondo import Mondo
from .ncit import NCIt
from .omim import OMIM
from .oncotree import OncoTree

__all__ = [
    "DO",
    "Merge",
    "Mondo",
    "NCIt",
    "OMIM",
    "OncoTree",
]
