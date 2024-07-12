"""Get OMIM disease data."""

from pathlib import Path

from tqdm import tqdm
from wags_tails import CustomData, DataSource

from disease.etl.base import Base
from disease.schemas import NamespacePrefix, SourceMeta


class OMIM(Base):
    """Gather and load data from OMIM."""

    def _raise_access_error(self) -> None:
        """Raise improper data access error and describe proper data access."""
        msg = f"Could not locate OMIM data. Per README, OMIM source files must be manually placed in {self._data_source.data_dir.absolute().as_uri()}"
        raise FileNotFoundError(msg)

    def _get_data_handler(self, data_path: Path | None = None) -> DataSource:
        """Construct data handler instance for source. Overwrites base class method
        to use custom data handler instead.

        :param data_path: location of data storage
        :return: instance of wags_tails.DataSource to manage source file(s)
        """
        return CustomData(
            "omim",
            "tsv",
            latest_version_cb=lambda: "",
            download_cb=lambda: self._raise_access_error(),
            data_dir=data_path,
        )

    def _extract_data(self, use_existing: bool = False) -> None:  # noqa: ARG002
        """Get source file from data directory.

        :param use_existing: if True, use local data regardless of whether it's up to
            date. OMIM data must be manually provided, so this argument is ignored.
        """
        self._data_file, self._version = self._data_source.get_latest(from_local=True)

    def _load_meta(self) -> None:
        """Load source metadata."""
        metadata = SourceMeta(
            data_license="custom",
            data_license_url="https://omim.org/help/agreement",
            version=self._data_file.stem.split("_", 1)[1],
            data_url="https://www.omim.org/downloads",
            rdp_url="http://reusabledata.org/omim.html",
            data_license_attributes={
                "non_commercial": False,
                "share_alike": True,
                "attribution": True,
            },
        )
        self._database.add_source_metadata(self._src_name, metadata)

    def _transform_data(self) -> None:
        """Modulate data and prepare for loading."""
        with self._data_file.open() as f:
            rows = f.readlines()
        rows = [r.rstrip() for r in rows if not r.startswith("#")]
        rows = [r.split("\t") for r in rows]
        rows = [r for r in rows if r[0] not in ("Asterisk", "Caret", "Plus")]
        for row in tqdm(rows, ncols=80, disable=self._silent):
            disease = {
                "concept_id": f"{NamespacePrefix.OMIM.value}:{row[1]}",
            }
            aliases = set()

            label_item = row[2]
            if ";" in label_item:
                label_split = label_item.split(";")
                disease["label"] = label_split[0]
                aliases.add(label_split[1])
            else:
                disease["label"] = row[2]

            if len(row) > 3:
                aliases |= {t for t in row[3].split(";") if t}
            if len(row) > 4:
                aliases |= {t for t in row[4].split(";") if t}
            aliases = {
                alias[:-10] if alias.endswith(", INCLUDED") else alias
                for alias in aliases
            }
            disease["aliases"] = [a.lstrip() for a in aliases]

            self._load_disease(disease)
