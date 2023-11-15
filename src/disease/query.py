"""Provides methods for handling queries."""
import re
from datetime import datetime
from typing import Dict, Optional, Set, Tuple

from botocore.exceptions import ClientError
from ga4gh.core import core_models

from disease import NAMESPACE_LOOKUP, PREFIX_LOOKUP, SOURCES_LOWER_LOOKUP, logger
from disease.database.database import AbstractDatabase
from disease.schemas import (
    Disease,
    MatchType,
    NormalizationService,
    RefType,
    SearchService,
    ServiceMeta,
    SourceName,
)

from .version import __version__


class InvalidParameterException(Exception):  # noqa: N818
    """Exception for invalid parameter args provided by the user."""


class QueryHandler:
    """Class for normalizer management. Stores reference to database instance
    and normalizes query input.
    """

    def __init__(self, database: AbstractDatabase) -> None:
        """Initialize Normalizer instance.

        :param database: storage backend to query against
        """
        self.db = database

    def _emit_warnings(self, query_str: str) -> Optional[Dict]:
        """Emit warnings if query contains non breaking space characters.
        :param str query_str: query string
        :return: dict keying warning type to warning description
        """
        warnings = None
        nbsp = re.search("\xa0|&nbsp;", query_str)
        if nbsp:
            warnings = {"nbsp": "Query contains non breaking space characters."}
            logger.warning(
                f"Query ({query_str}) contains non breaking space characters."
            )
        return warnings

    def _add_record(
        self, response: Dict[str, Dict], item: Dict, match_type: str
    ) -> Tuple[Dict, str]:
        """Add individual record to response object

        :param Dict[str, Dict] response: in-progress response object to return
            to client
        :param Dict item: Item retrieved from DynamoDB
        :param str match_type: type of query match
        :return: Tuple containing updated response object, and string
            containing name of the source of the match
        """
        disease = Disease(**item)
        src_name = item["src_name"]

        matches = response["source_matches"]
        if src_name not in matches.keys():
            pass
        elif matches[src_name] is None:
            matches[src_name] = {
                "match_type": MatchType[match_type.upper()],
                "records": [disease],
                "source_meta_": self.db.get_source_metadata(src_name),
            }
        elif matches[src_name]["match_type"] == MatchType[match_type.upper()]:
            matches[src_name]["records"].append(disease)

        return response, src_name

    def _fetch_records(
        self, response: Dict[str, Dict], concept_ids: Set[str], match_type: str
    ) -> Tuple[Dict, Set]:
        """Return matched Disease records as a structured response for a given
        collection of concept IDs.

        :param Dict[str, Dict] response: in-progress response object to return
            to client.
        :param List[str] concept_ids: List of concept IDs to build from.
            Should be all lower-case.
        :param str match_type: record should be assigned this type of match.
        :return: response Dict with records filled in via provided concept
            IDs, and Set of source names of matched records
        """
        matched_sources = set()
        for concept_id in concept_ids:
            try:
                match = self.db.get_record_by_id(
                    concept_id.lower(), case_sensitive=False
                )
                if match is None:
                    logger.error(f"Reference to {concept_id} failed.")
                else:
                    (response, src) = self._add_record(response, match, match_type)
                    matched_sources.add(src)
            except ClientError as e:
                logger.error(e.response["Error"]["Message"])
        return response, matched_sources

    def _fill_no_matches(self, resp: Dict[str, Dict]) -> Dict:
        """Fill all empty source_matches slots with NO_MATCH results.

        :param Dict[str, Dict] resp: incoming response object
        :return: response object with empty source slots filled with
                NO_MATCH results and corresponding source metadata
        """
        for src_name in resp["source_matches"].keys():
            if resp["source_matches"][src_name] is None:
                resp["source_matches"][src_name] = {
                    "match_type": MatchType.NO_MATCH,
                    "records": [],
                    "source_meta_": self.db.get_source_metadata(src_name),
                }
        return resp

    def _check_concept_id(
        self, query: str, resp: Dict, sources: Set[str]
    ) -> Tuple[Dict, Set]:
        """Check query for concept ID match. Should only find 0 or 1 matches.

        :param str query: search string
        :param Dict resp: in-progress response object to return to client
        :param Set[str] sources: remaining unmatched sources
        :return: Tuple with updated resp object and updated set of unmatched
            sources
        """
        concept_id_items = []
        if [p for p in PREFIX_LOOKUP.keys() if query.startswith(p)]:
            record = self.db.get_record_by_id(query, False)
            if record:
                concept_id_items.append(record)
        for prefix in [p for p in NAMESPACE_LOOKUP.keys() if query.startswith(p)]:
            concept_id = f"{NAMESPACE_LOOKUP[prefix]}:{query}"
            id_lookup = self.db.get_record_by_id(concept_id, False)
            if id_lookup:
                concept_id_items.append(id_lookup)
        for item in concept_id_items:
            (resp, src_name) = self._add_record(resp, item, MatchType.CONCEPT_ID.name)
            sources = sources - {src_name}
        return resp, sources

    def _check_match_type(
        self, query: str, resp: Dict, sources: Set[str], match_type: RefType
    ) -> Tuple[Dict, Set]:
        """Check query for selected match type.

        :param str query: search string
        :param Dict resp: in-progress response object to return to client
        :param Set[str] sources: remaining unmatched sources
        :param RefType match_type: Match type to check for. Should be one of
            {'label', 'alias', 'xref', 'associated_with'}
        :return: Tuple with updated resp object and updated set of unmatched
                 sources
        """
        matching_ids = self.db.get_refs_by_type(query, match_type)
        if matching_ids:
            (resp, matched_srcs) = self._fetch_records(
                resp, set(matching_ids), match_type
            )
            sources = sources - matched_srcs
        return resp, sources

    def _get_search_response(self, query: str, sources: Set[str]) -> Dict:
        """Return response as dict where key is source name and value is a list of
        records.

        :param str query: string to match against
        :param Set[str] sources: sources to match from
        :return: completed response object to return to client
        """
        response = {
            "query": query,
            "warnings": self._emit_warnings(query),
            "source_matches": {source: None for source in sources},
        }
        if query == "":
            response = self._fill_no_matches(response)
            return response
        query = query.lower()

        # check if concept ID match
        (response, sources) = self._check_concept_id(query, response, sources)
        if len(sources) == 0:
            return response

        for match_type in RefType:
            (response, sources) = self._check_match_type(
                query, response, sources, match_type
            )
            if len(sources) == 0:
                return response

        # remaining sources get no match
        return self._fill_no_matches(response)

    def search(self, query_str: str, incl: str = "", excl: str = "") -> SearchService:
        """Fetch normalized disease objects.

        :param str query_str: query, a string, to search for
        :param str incl: str containing comma-separated names of sources to
            use. Will exclude all other sources. Case-insensitive.
        :param str excl: str containing comma-separated names of source to
            exclude. Will include all other source. Case-insensitive.
        :return: dict containing all matches found in sources.
        :rtype: dict
        :raises InvalidParameterException: if both incl and excl args are
            provided, or if invalid source names are given.
        """
        sources = dict()
        for k, v in SOURCES_LOWER_LOOKUP.items():
            if self.db.get_source_metadata(v):
                sources[k] = v
        if not incl and not excl:
            query_sources = set(sources.values())
        elif incl and excl:
            detail = "Cannot request both source inclusions and exclusions."
            raise InvalidParameterException(detail)
        elif incl:
            req_sources = [n.strip() for n in incl.split(",")]
            invalid_sources = []
            query_sources = set()
            for source in req_sources:
                if source.lower() in sources.keys():
                    query_sources.add(sources[source.lower()])
                else:
                    invalid_sources.append(source)
            if invalid_sources:
                detail = f"Invalid source name(s): {invalid_sources}"
                raise InvalidParameterException(detail)
        else:
            req_exclusions = [n.strip() for n in excl.lower().split(",")]
            req_excl_dict = {r.lower(): r for r in req_exclusions}
            invalid_sources = []
            query_sources = set()
            for req_l, req in req_excl_dict.items():
                if req_l not in sources.keys():
                    invalid_sources.append(req)
            for src_l, src in sources.items():
                if src_l not in req_excl_dict.keys():
                    query_sources.add(src)
            if invalid_sources:
                detail = f"Invalid source name(s): {invalid_sources}"
                raise InvalidParameterException(detail)

        query_str = query_str.strip()

        response = self._get_search_response(query_str, query_sources)

        response["service_meta_"] = ServiceMeta(
            version=__version__,
            response_datetime=datetime.now(),
        ).model_dump()
        return SearchService(**response)

    def _add_merged_meta(self, response: Dict) -> Dict:
        """Add source metadata to response object.

        :param Dict response: in-progress response object
        :return: completed response object.
        """
        sources_meta = {}
        disease = response["disease"]
        sources = [response["normalized_id"].split(":")[0]]
        if disease.mappings:
            sources += [m.coding.system for m in disease.mappings]

        for src in sources:
            try:
                src_name = PREFIX_LOOKUP[src]
            except KeyError:
                # not an imported source
                continue
            else:
                if src_name not in sources_meta:
                    sources_meta[src_name] = self.db.get_source_metadata(src_name)
        response["source_meta_"] = sources_meta
        return response

    def _add_disease(
        self, response: Dict, record: Dict, match_type: MatchType
    ) -> NormalizationService:
        """Format received DB record as core Disease object and update response object.

        :param response: in-progress response object
        :param record: record as stored in DB
        :param match_type: type of match achieved
        :return: completed normalized response object ready to return to user
        """
        disease_obj = core_models.Disease(
            id=f"normalize.disease.{record['concept_id']}", label=record["label"]
        )

        source_ids = record.get("xrefs", []) + record.get("associated_with", [])
        mappings = []
        for source_id in source_ids:
            system, code = source_id.split(":")
            mappings.append(
                core_models.Mapping(
                    coding=core_models.Coding(
                        code=core_models.Code(code), system=system.lower()
                    ),
                    relation=core_models.Relation.RELATED_MATCH,
                )
            )
        if mappings:
            disease_obj.mappings = mappings

        if "aliases" in record:
            disease_obj.aliases = record["aliases"]

        if "pediatric_disease" in record and record["pediatric_disease"] is not None:
            disease_obj.extensions = [
                core_models.Extension(
                    name="pediatric_disease",
                    value=record["pediatric_disease"],
                )
            ]

        response["match_type"] = match_type
        response["disease"] = disease_obj
        response["normalized_id"] = record["concept_id"]
        response = self._add_merged_meta(response)
        return NormalizationService(**response)

    def _record_order(self, record: Dict) -> Tuple[int, str]:
        """Construct priority order for matching. Only called by sort().

        :param Dict record: individual record item in iterable to sort
        :return: tuple with rank value and concept ID
        """
        src = record["src_name"]
        if src == SourceName.NCIT.value:
            source_rank = 1
        elif src == SourceName.MONDO.value:
            source_rank = 2
        elif src == SourceName.ONCOTREE.value:
            source_rank = 3
        elif src == SourceName.OMIM.value:
            source_rank = 4
        elif src == SourceName.DO.value:
            source_rank = 5
        else:
            logger.warning(f"query.record_order: Invalid source name for " f"{record}")
            source_rank = 4
        return source_rank, record["concept_id"]

    def _handle_failed_merge_ref(
        self, record: Dict, response: Dict, query: str
    ) -> NormalizationService:
        """Log + fill out response for a failed merge reference lookup.

        :param Dict record: record containing failed merge_ref
        :param Dict response: in-progress response object
        :param str query: original query value
        :return: Normalized response with no match
        """
        logger.error(
            f"Merge ref lookup failed for ref {record['merge_ref']} "
            f"in record {record['concept_id']} from query {query}"
        )
        response["match_type"] = MatchType.NO_MATCH
        return NormalizationService(**response)

    def normalize(self, query: str) -> NormalizationService:
        """Return normalized concept for given search term.
        :param str query: string to search against
        :return: NormalizationService object with complete response
        """
        # prepare basic response
        response = {
            "match_type": MatchType.NO_MATCH,
            "query": query,
            "warnings": self._emit_warnings(query),
            "service_meta_": ServiceMeta(
                version=__version__,
                response_datetime=datetime.now(),
            ),
        }
        if query == "":
            return NormalizationService(**response)
        query_str = query.lower().strip()

        # check merged concept ID match
        record = self.db.get_record_by_id(query_str, case_sensitive=False, merge=True)
        if record:
            return self._add_disease(response, record, MatchType.CONCEPT_ID)

        non_merged_match = None

        # check concept ID match
        record = self.db.get_record_by_id(query_str, case_sensitive=False)
        if record:
            if "merge_ref" in record:
                merge = self.db.get_record_by_id(
                    record["merge_ref"], case_sensitive=False, merge=True
                )
                if merge is None:
                    return self._handle_failed_merge_ref(record, response, query_str)
                else:
                    return self._add_disease(response, merge, MatchType.CONCEPT_ID)
            else:
                non_merged_match = (record, "concept_id")

        # check other match types
        for match_type in RefType:
            # get matches list for match tier
            matching_refs = self.db.get_refs_by_type(query_str, match_type)
            matching_records = [
                self.db.get_record_by_id(ref, False) for ref in matching_refs
            ]
            matching_records.sort(key=self._record_order)  # type: ignore

            # attempt merge ref resolution until successful
            for match in matching_records:
                record = self.db.get_record_by_id(
                    match["concept_id"],
                    False,  # type: ignore
                )
                if record:
                    if "merge_ref" in record:
                        merge = self.db.get_record_by_id(
                            record["merge_ref"], case_sensitive=False, merge=True
                        )
                        if merge is None:
                            return self._handle_failed_merge_ref(
                                record, response, query_str
                            )
                        else:
                            return self._add_disease(
                                response, merge, MatchType[match_type.upper()]
                            )
                    else:
                        if not non_merged_match:
                            non_merged_match = (record, match_type)

        # if no successful match, try available non-merged match
        if non_merged_match:
            match_type = MatchType[non_merged_match[1].upper()]
            return self._add_disease(response, non_merged_match[0], match_type)

        return NormalizationService(**response)
