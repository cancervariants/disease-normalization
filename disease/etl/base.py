"""A base class for extraction, transformation, and loading of data."""
import tempfile
import zipfile
import os
from abc import ABC, abstractmethod
from typing import Set, Dict, List, Optional, Callable
from pathlib import Path
import re
import ftplib

from owlready2.rdflib_store import TripleLiteRDFlibGraph as RDFGraph
import bioversions
import requests

from disease import SOURCES_FOR_MERGE, ITEM_TYPES, logger, APP_ROOT
from disease.database import Database
from disease.schemas import Disease
from disease.etl.utils import DownloadException


DEFAULT_DATA_PATH = APP_ROOT / "data"


class Base(ABC):
    """The ETL base class."""

    def __init__(self, database: Database, data_path: Path = DEFAULT_DATA_PATH):
        """Extract from sources.
        :param database: DDB client
        :param data_path: location of data directory
        """
        self.name = self.__class__.__name__.lower()
        self.database = database
        self._src_dir: Path = Path(data_path / self.name)
        self._store_ids = self.__class__.__name__ in SOURCES_FOR_MERGE
        if self._store_ids:
            self._added_ids = []

    def perform_etl(self, use_existing: bool = False) -> List:
        """Public-facing method to begin ETL procedures on given data.
        :param use_existing: if True, use local data instead of retrieving most recent
        version
        :return: List of concept IDs to be added to merge generation.
        """
        self._extract_data(use_existing)
        self._load_meta()
        self._transform_data()
        if self._store_ids:
            return self._added_ids
        else:
            return []

    def get_latest_version(self) -> str:
        """Get most recent version of source data. Should be overriden by
        sources not added to Bioversions yet, or other special-case sources.
        :return: most recent version, as a str
        """
        return bioversions.get_version(self.name)

    @abstractmethod
    def _download_data(self):
        """Download source data."""
        raise NotImplementedError

    def _zip_handler(self, dl_path: Path, outfile_path: Path) -> None:
        """Provide simple callback function to extract the largest file within a given
        zipfile and save it within the appropriate data directory.
        :param Path dl_path: path to temp data file
        :param Path outfile_path: path to save file within
        """
        with zipfile.ZipFile(dl_path, "r") as zip_ref:
            if len(zip_ref.filelist) > 1:
                files = sorted(zip_ref.filelist, key=lambda z: z.file_size,
                               reverse=True)
                target = files[0]
            else:
                target = zip_ref.filelist[0]
            target.filename = outfile_path.name
            zip_ref.extract(target, path=outfile_path.parent)
        os.remove(dl_path)

    @staticmethod
    def _http_download(url: str, outfile_path: Path, headers: Optional[Dict] = None,
                       handler: Optional[Callable[[Path, Path], None]] = None) -> None:
        """Perform HTTP download of remote data file.
        :param str url: URL to retrieve file from
        :param Path outfile_path: path to where file should be saved. Must be an actual
            Path instance rather than merely a pathlike string.
        :param Optional[Dict] headers: Any needed HTTP headers to include in request
        :param Optional[Callable[[Path, Path], None]] handler: provide if downloaded
            file requires additional action, e.g. it's a zip file.
        """
        if handler:
            dl_path = Path(tempfile.gettempdir()) / "therapy_dl_tmp"
        else:
            dl_path = outfile_path
        # use stream to avoid saving download completely to memory
        with requests.get(url, stream=True, headers=headers) as r:
            try:
                r.raise_for_status()
            except requests.HTTPError:
                raise DownloadException(
                    f"Failed to download {outfile_path.name} from {url}."
                )
            with open(dl_path, "wb") as h:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        h.write(chunk)
        if handler:
            handler(dl_path, outfile_path)

    def _ftp_download(self, host: str, host_dir: str, host_fn: str) -> None:
        """Download data file from FTP site.
        :param str host: Source's FTP host name
        :param str host_dir: Data directory located on FTP site
        :param str host_fn: Filename on FTP site to be downloaded
        """
        try:
            with ftplib.FTP(host) as ftp:
                ftp.login()
                logger.debug(f"FTP login to {host} was successful")
                ftp.cwd(host_dir)
                with open(self._src_dir / host_fn, "wb") as fp:
                    ftp.retrbinary(f"RETR {host_fn}", fp.write)
        except ftplib.all_errors as e:
            logger.error(f"FTP download failed: {e}")
            raise Exception(e)

    def _parse_version(self, file_path: Path, pattern: Optional[re.Pattern] = None
                       ) -> str:
        """Get version number from provided file path.
        :param Path file_path: path to located source data file
        :param Optional[re.Pattern] pattern: regex pattern to use
        :return: source data version
        :raises: FileNotFoundError if version parsing fails
        """
        if pattern is None:
            pattern = re.compile(type(self).__name__.lower() + r"_(.+)\..+")
        matches = re.match(pattern, file_path.name)
        if matches is None:
            raise FileNotFoundError
        else:
            return matches.groups()[0]

    def _get_latest_data_file(self) -> Path:
        """Acquire most recent source data file."""
        self._version = self.get_latest_version()
        fglob = f"{self.name}_{self._version}.*"
        latest = list(self._src_dir.glob(fglob))
        if not latest:
            self._download_data()
            latest = list(self._src_dir.glob(fglob))
        assert len(latest) != 0  # probably unnecessary, but just to be safe
        return latest[0]

    def _extract_data(self, use_existing: bool = False) -> None:
        """Get source file from data directory.
        :param use_existing: if True, use local data regardless of whether it's up to
            date
        """
        self._src_dir.mkdir(exist_ok=True, parents=True)
        src_name = type(self).__name__.lower()
        if use_existing:
            files = list(sorted(self._src_dir.glob(f"{src_name}_*.*")))
            if len(files) < 1:
                raise FileNotFoundError(f"No source data found for {src_name}")
            self._data_file: Path = files[-1]
            try:
                self._version = self._parse_version(self._data_file)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Unable to parse version value from {src_name} source data file "
                    f"located at {self._data_file.absolute().as_uri()} -- "
                    "check filename against schema defined in README: "
                    "https://github.com/cancervariants/therapy-normalization#update-sources"  # noqa: E501
                )
        else:
            self._data_file = self._get_latest_data_file()

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

        for attr_type, item_type in ITEM_TYPES.items():
            if attr_type in disease:
                value = disease[attr_type]
                if value is not None and value != []:
                    if isinstance(value, str):
                        items = [value.lower()]
                    else:
                        disease[attr_type] = list(set(value))
                        items = {item.lower() for item in value}
                        if attr_type == 'aliases':
                            if len(items) > 20:
                                logger.debug(f"{concept_id} has > 20 aliases.")
                                del disease[attr_type]
                                continue

                    for item in items:
                        self.database.add_ref_record(item, concept_id,
                                                     item_type)
                else:
                    del disease[attr_type]

        if 'pediatric_disease' in disease \
                and disease['pediatric_disease'] is None:
            del disease['pediatric_disease']

        self.database.add_record(disease)
        if self._store_ids:
            self._added_ids.append(concept_id)


class OWLBase(Base):
    """Base class for sources that use OWL files."""

    def _get_subclasses(self, uri: str, graph: RDFGraph) -> Set[str]:
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
    ) -> Set[str]:
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
