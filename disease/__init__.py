"""The VICC library for normalizing diseases."""
from pathlib import Path
import logging

from .version import __version__  # noqa: F401


APP_ROOT = Path(__file__).resolve().parents[0]

# set up logging
logging.basicConfig(
    filename="disease.log",
    format="[%(asctime)s] - %(name)s - %(levelname)s : %(message)s"
)
logger = logging.getLogger("disease")
logger.setLevel(logging.DEBUG)
logger.handlers = []


class DownloadException(Exception):
    """Exception for failures relating to source file downloads."""

    def __init__(self, *args, **kwargs):
        """Initialize exception."""
        super().__init__(*args, **kwargs)


from disease.schemas import SourceName, SourceIDAfterNamespace, NamespacePrefix, ItemTypes  # noqa: E402 E501
ITEM_TYPES = {k.lower(): v.value for k, v in ItemTypes.__members__.items()}

# use to lookup source name from lower-case string
# technically the same as PREFIX_LOOKUP, but source namespace prefixes
# sometimes differ from their names
# e.g. {'ncit': 'NCIt'}
SOURCES_LOWER_LOOKUP = {name.value.lower(): name.value for name in
                        SourceName.__members__.values()}

# use to fetch source name from schema based on concept id namespace
# e.g. {'ncit': 'NCIt', 'doid': 'DO'}
PREFIX_LOOKUP = {v.value.lower(): SourceName[k].value
                 for k, v in NamespacePrefix.__members__.items()
                 if k in SourceName.__members__.keys()}

# use to generate namespace prefix from source ID value
# e.g. {'c': 'NCIt'}
NAMESPACE_LOOKUP = {v.value.lower(): NamespacePrefix[k].value
                    for k, v in SourceIDAfterNamespace.__members__.items()
                    if v.value != ''}

# Use for checking whether to pull IDs for merge group generation
SOURCES_FOR_MERGE = {SourceName.MONDO.value}
