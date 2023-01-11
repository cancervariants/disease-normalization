"""Module to load disease data from Mondo Disease Ontology."""
from itertools import groupby
from typing import Dict, List, Optional

import owlready2 as owl
import requests
from owlready2.rdflib_store import TripleLiteRDFlibGraph as RDFGraph

from disease import PREFIX_LOOKUP, logger
from disease.schemas import NamespacePrefix, SourceMeta, SourceName

from .base import OWLBase

MONDO_PREFIX_LOOKUP = {
    "http://purl.obolibrary.org/obo/MONDO": NamespacePrefix.MONDO.value,
    # xref
    "http://purl.obolibrary.org/obo/DOID": NamespacePrefix.DO.value,
    "DOID": NamespacePrefix.DO.value,
    "https://omim.org/entry": NamespacePrefix.OMIM.value,
    "OMIM": NamespacePrefix.OMIM.value,
    "http://purl.obolibrary.org/obo/NCIT": NamespacePrefix.NCIT.value,
    "NCIT": NamespacePrefix.NCIT.value,
    "ONCOTREE": NamespacePrefix.ONCOTREE.value,
    # associated_with
    "SCDO": NamespacePrefix.SCDO.value,
    "Orphanet": NamespacePrefix.ORPHANET.value,
    "http://www.orpha.net/ORDO/Orphanet": NamespacePrefix.ORPHANET.value,
    "UMLS": NamespacePrefix.UMLS.value,
    "http://linkedlifedata.com/resource/umls/id": NamespacePrefix.UMLS.value,
    "https://omim.org/phenotypicSeries": NamespacePrefix.OMIMPS.value,
    "http://purl.bioontology.org/ontology/ICD10CM": NamespacePrefix.ICD10CM.value,
    "efo": NamespacePrefix.EFO.value,
    "EFO": NamespacePrefix.EFO.value,
    "GARD": NamespacePrefix.GARD.value,
    "HP": NamespacePrefix.HPO.value,
    "ICD9": NamespacePrefix.ICD9.value,
    "ICD9CM": NamespacePrefix.ICD9CM.value,
    "ICD10WHO": NamespacePrefix.ICD10.value,
    "https://icd.who.int/browse10/2019/en#": NamespacePrefix.ICD10.value,
    "ICD10CM": NamespacePrefix.ICD10CM.value,
    "ICD11": NamespacePrefix.ICD11.value,
    "DECIPHER": NamespacePrefix.DECIPHER.value,
    "MEDGEN": NamespacePrefix.MEDGEN.value,
    "http://identifiers.org/medgen": NamespacePrefix.MEDGEN.value,
    "MESH": NamespacePrefix.MESH.value,
    "http://identifiers.org/mesh": NamespacePrefix.MESH.value,
    "MPATH": NamespacePrefix.MPATH.value,
    "MedDRA": NamespacePrefix.MEDDRA.value,
    "http://identifiers.org/meddra": NamespacePrefix.MEDDRA.value,
    "OBI": NamespacePrefix.OBI.value,
    "OGMS": NamespacePrefix.OGMS.value,
    "OMIMPS": NamespacePrefix.OMIMPS.value,
    "Wikidata": NamespacePrefix.WIKIDATA.value,
}


class Mondo(OWLBase):
    """Gather and load data from Mondo."""

    def get_latest_version(self) -> str:
        """Get most recent version of MONDO from GitHub API.
        :return: Most recent version, as a str
        """
        response = requests.get(
            "https://api.github.com/repos/monarch-initiative/mondo/releases/latest"
        )
        if response.status_code == 200:
            return response.json()["name"].replace("v", "")
        else:
            raise requests.HTTPError(
                f"Unable to retrieve MONDO version from GitHub "
                f"API. Status code: {response.status_code}"
            )

    def _download_data(self):
        """Download Mondo thesaurus source file for loading into normalizer."""
        logger.info("Downloading Mondo data...")
        url = f"http://purl.obolibrary.org/obo/mondo/releases/{self._version}/mondo.owl"
        output_file = self._src_dir / f"mondo_{self._version}.owl"
        self._http_download(url, output_file)
        logger.info("Finished downloading Mondo Disease Ontology")

    def _load_meta(self):
        """Load metadata"""
        metadata = SourceMeta(
            data_license="CC BY 4.0",
            data_license_url="https://creativecommons.org/licenses/by/4.0/legalcode",
            version=self._version,
            data_url="https://mondo.monarchinitiative.org/pages/download/",
            rdp_url="http://reusabledata.org/monarch.html",
            data_license_attributes={
                "non_commercial": False,
                "share_alike": False,
                "attribution": True,
            },
        )
        params = dict(metadata)
        params["src_name"] = SourceName.MONDO.value
        self.database.metadata.put_item(Item=params)

    def _get_concept_id(self, ref: str) -> Optional[str]:
        """Format concept ID for given reference.
        :param ref: may be an IRI or other concept code structure
        :return: standardized concept ID if successful
        """
        if ref.startswith("http"):
            if "snomedct" in ref:
                return None
            elif ref.startswith(("http://purl.obo", "http://www.orpha")):
                prefix, id_no = ref.split("_")
            else:
                prefix, id_no = ref.rsplit("/", 1)
        else:
            if ref.startswith("SCTID"):
                return None
            elif "/" in ref:
                prefix, id_no = ref.rsplit("/", 1)
            else:
                try:
                    prefix, id_no = ref.split(":")
                except ValueError as e:
                    logger.warning(
                        f"{ref} raised a ValueError when trying to get "
                        f"prefix and ID: {e}"
                    )
                    return None
        try:
            concept_id = f"{MONDO_PREFIX_LOOKUP[prefix]}:{id_no}"
        except KeyError:
            logger.warning(f"Unable to produce concept ID for reference: {ref}")
            return None
        return concept_id

    def _get_equivalent_xrefs(self, graph: RDFGraph) -> Dict[str, List[Optional[str]]]:
        """Extract all MONDO:equivalentTo relations.
        :param graph: RDFLib graph produced from OWL default world
        :return: MONDO terms mapped to their equivalence relations
        """
        equiv_annotations_query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            prefix oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

            SELECT ?source ?child
            WHERE {
                ?annotation owl:annotatedSource ?source ;
                            owl:annotatedTarget ?child ;
                            oboInOwl:source "MONDO:equivalentTo"
            }
        """
        equiv_rels_result = graph.query(equiv_annotations_query)
        grouped = groupby(
            equiv_rels_result, lambda i: i[0].split("_")[1]  # type: ignore
        )
        keyed = {
            str(key): [self._get_concept_id(g[1]) for g in group]  # type: ignore
            for key, group in grouped
        }
        return keyed

    def _transform_data(self):
        """Gather and transform disease entities."""
        mondo = owl.get_ontology(self._data_file.absolute().as_uri()).load()
        graph = owl.default_world.as_rdflib_graph()

        # gather constants/search materials
        disease_root = "http://purl.obolibrary.org/obo/MONDO_0000001"
        disease_uris = self._get_subclasses(disease_root, graph)
        peds_neoplasm_root = "http://purl.obolibrary.org/obo/MONDO_0006517"
        peds_uris = self._get_subclasses(peds_neoplasm_root, graph)
        equiv_rels = self._get_equivalent_xrefs(graph)

        for uri in disease_uris:
            try:
                disease = mondo.search_one(iri=uri)
            except TypeError:
                logger.error(
                    f"Mondo.transform_data could not retrieve class " f"for URI {uri}"
                )
                continue
            try:
                label = disease.label[0]
            except IndexError:
                logger.debug(f"No label for Mondo concept {uri}")
                continue

            concept_id = disease.id[0].lower()
            aliases = list({d for d in disease.hasExactSynonym if d != label})
            params = {
                "concept_id": concept_id,
                "label": label,
                "aliases": aliases,
                "xrefs": [],
                "associated_with": [],
            }
            exact_matches = {self._get_concept_id(m) for m in disease.exactMatch}
            equiv_xrefs = equiv_rels.get(concept_id.split(":")[1], set())
            xrefs = {x for x in exact_matches.union(equiv_xrefs) if x}

            for ref in xrefs:
                if ref.split(":")[0].lower() in PREFIX_LOOKUP:
                    params["xrefs"].append(ref)
                else:
                    params["associated_with"].append(ref)

            if disease.iri in peds_uris:
                params["pediatric_disease"] = True

            self._load_disease(params)
