"""Module to load disease data from OMIM."""
from disease import DownloadException, logger
from disease.schemas import Disease, NamespacePrefix, SourceMeta, SourceName

from .base import Base


class OMIM(Base):
    """Gather and load data from OMIM."""

    def _extract_data(self, use_existing: bool = False):
        """Override parent extract method to enforce OMIM-specific data file
        requirements.
        :param use_existing: technically non-functional, but included to match
        sibling method signatures. If True, will print warning but otherwise proceed.
        """
        if not use_existing:
            logger.warning(
                "Overruling provided `use_existing` parameter. OMIM data is not "
                "publicly available - see README for details - and must be manually "
                f"placed in {self._src_dir.absolute().as_uri()}"
            )
        try:
            super()._extract_data(True)
        except FileNotFoundError:
            raise FileNotFoundError(
                "Could not locate OMIM data. Per README, OMIM "
                "source files must be manually placed in "
                f"{self._src_dir.absolute().as_uri()}"
            )

    def _download_data(self):
        """Download OMIM source data for loading into normalizer."""
        raise DownloadException("OMIM data not available for public download")

    def _load_meta(self):
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
        params = dict(metadata)
        params["src_name"] = SourceName.OMIM.value
        self.database.metadata.put_item(Item=params)

    def _transform_data(self):
        """Modulate data and prepare for loading."""
        with open(self._data_file, "r") as f:
            rows = f.readlines()
        rows = [r.rstrip() for r in rows if not r.startswith("#")]
        rows = [[g for g in r.split("\t")] for r in rows]
        rows = [r for r in rows if r[0] not in ("Asterisk", "Caret", "Plus")]
        for row in rows:
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

            assert Disease(**disease)
            self._load_disease(disease)
