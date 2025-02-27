"""Module to load and init namespace at package level."""

from .base import DiseaseNormalizerEtlError
from .do import DO
from .merge import Merge
from .mondo import Mondo
from .ncit import NCIt
from .omim import OMIM
from .oncotree import OncoTree

__all__ = [
    "DO",
    "OMIM",
    "DiseaseNormalizerEtlError",
    "Merge",
    "Mondo",
    "NCIt",
    "OncoTree",
]
