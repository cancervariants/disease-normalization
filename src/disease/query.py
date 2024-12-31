"""Provides query handler class, which receives and responses to user search queries."""

import datetime
import logging
import re

from botocore.exceptions import ClientError
from ga4gh.core.models import (
    Coding,
    ConceptMapping,
    Extension,
    MappableConcept,
    Relation,
    code,
)

from disease import NAMESPACE_LOOKUP, PREFIX_LOOKUP, SOURCES_LOWER_LOOKUP, __version__
from disease.database.database import AbstractDatabase
from disease.schemas import (
    NAMESPACE_TO_SYSTEM_URI,
    SYSTEM_URI_TO_NAMESPACE,
    Disease,
    MatchType,
    NamespacePrefix,
    NormalizationService,
    RefType,
    SearchService,
    ServiceMeta,
    SourceName,
)

_logger = logging.getLogger(__name__)


class InvalidParameterException(Exception):  # noqa: N818
    """Exception for invalid parameter args provided by the user."""


class QueryHandler:
    """Class for normalizer management. Stores reference to database instance
    and normalizes query input.
    """

    def __init__(self, database: AbstractDatabase) -> None:
        """Initialize QueryHandler instance. Requires a created database object to
        initialize. The most straightforward way to do this is via the
        :py:meth:`~disease.database.database.create_db` method:

        >>> from disease.query import QueryHandler
        >>> from disease.database import create_db
        >>> q = QueryHandler(create_db())

        We'll generally call ``create_db`` without any arguments in code examples, for
        the sake of brevity. See the :py:meth:`~disease.database.database.create_db` API
        description for more details.

        :param database: storage backend to search against
        """
        self.db = database

    def _emit_warnings(self, query_str: str) -> dict | None:
        """Emit warnings if query contains non breaking space characters.
        :param str query_str: query string
        :return: dict keying warning type to warning description
        """
        warnings = None
        nbsp = re.search("\xa0|&nbsp;", query_str)
        if nbsp:
            warnings = {"nbsp": "Query contains non breaking space characters."}
            _logger.warning(
                "Query (%s) contains non breaking space characters.", query_str
            )
        return warnings

    def _add_record(
        self, response: dict[str, dict], item: dict, match_type: str
    ) -> tuple[dict, str]:
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
        if src_name not in matches:
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
        self, response: dict[str, dict], concept_ids: set[str], match_type: str
    ) -> tuple[dict, set]:
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

        try:
            for concept_id in concept_ids:
                match = self.db.get_record_by_id(
                    concept_id.lower(), case_sensitive=False
                )
                if match is None:
                    _logger.error("Reference to %s failed.", concept_id)
                else:
                    (response, src) = self._add_record(response, match, match_type)
                    matched_sources.add(src)
        except ClientError as e:
            _logger.error(e.response["Error"]["Message"])
        return response, matched_sources

    def _fill_no_matches(self, resp: dict[str, dict]) -> dict:
        """Fill all empty source_matches slots with NO_MATCH results.

        :param Dict[str, Dict] resp: incoming response object
        :return: response object with empty source slots filled with
                NO_MATCH results and corresponding source metadata
        """
        for src_name in resp["source_matches"]:
            if resp["source_matches"][src_name] is None:
                resp["source_matches"][src_name] = {
                    "match_type": MatchType.NO_MATCH,
                    "records": [],
                    "source_meta_": self.db.get_source_metadata(src_name),
                }
        return resp

    def _check_concept_id(
        self, query: str, resp: dict, sources: set[str]
    ) -> tuple[dict, set]:
        """Check query for concept ID match. Should only find 0 or 1 matches.

        :param str query: search string
        :param Dict resp: in-progress response object to return to client
        :param Set[str] sources: remaining unmatched sources
        :return: Tuple with updated resp object and updated set of unmatched
            sources
        """
        concept_id_items = []
        if [p for p in PREFIX_LOOKUP if query.startswith(p)]:
            record = self.db.get_record_by_id(query, False)
            if record:
                concept_id_items.append(record)
        for prefix in [p for p in NAMESPACE_LOOKUP if query.startswith(p)]:
            concept_id = f"{NAMESPACE_LOOKUP[prefix]}:{query}"
            id_lookup = self.db.get_record_by_id(concept_id, False)
            if id_lookup:
                concept_id_items.append(id_lookup)
        for item in concept_id_items:
            (resp, src_name) = self._add_record(resp, item, MatchType.CONCEPT_ID.name)
            sources = sources - {src_name}
        return resp, sources

    def _check_match_type(
        self, query: str, resp: dict, sources: set[str], match_type: RefType
    ) -> tuple[dict, set]:
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

    def _get_search_response(self, query: str, sources: set[str]) -> dict:
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
            return self._fill_no_matches(response)
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
        """Return highest match for each source.

        >>> from disease.query import QueryHandler
        >>> from disease.database import create_db
        >>> q = QueryHandler(create_db())
        >>> result = q.search("NSCLC")
        >>> result.source_matches["Mondo"].records[0].concept_id
        'mondo:0005233'

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
        sources = {
            k: v
            for k, v in SOURCES_LOWER_LOOKUP.items()
            if self.db.get_source_metadata(v)
        }

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
                if source.lower() in sources:
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
                if req_l not in sources:
                    invalid_sources.append(req)
            for src_l, src in sources.items():
                if src_l not in req_excl_dict:
                    query_sources.add(src)
            if invalid_sources:
                detail = f"Invalid source name(s): {invalid_sources}"
                raise InvalidParameterException(detail)

        query_str = query_str.strip()

        response = self._get_search_response(query_str, query_sources)

        response["service_meta_"] = ServiceMeta(
            version=__version__,
            response_datetime=datetime.datetime.now(tz=datetime.UTC),
        ).model_dump()
        return SearchService(**response)

    def _add_merged_meta(self, response: dict) -> dict:
        """Add source metadata to response object.

        :param Dict response: in-progress response object
        :return: completed response object.
        """
        sources_meta = {}
        disease = response["disease"]

        sources = []
        for m in disease.mappings or []:
            ns = SYSTEM_URI_TO_NAMESPACE.get(m.coding.system, "").lower()
            if ns in PREFIX_LOOKUP:
                sources.append(PREFIX_LOOKUP[ns])

        for src in sources:
            if src not in sources_meta:
                sources_meta[src] = self.db.get_source_metadata(src)
        response["source_meta_"] = sources_meta
        return response

    def _add_disease(
        self, response: dict, record: dict, match_type: MatchType
    ) -> NormalizationService:
        """Format received DB record as core Disease object and update response object.

        :param response: in-progress response object
        :param record: record as stored in DB
        :param match_type: type of match achieved
        :return: completed normalized response object ready to return to user
        """

        def _create_concept_mapping(
            concept_id: str, relation: Relation = Relation.RELATED_MATCH
        ) -> ConceptMapping:
            """Create concept mapping for identifier

            ``system`` will use OBO Foundry persistent URL (PURL), source homepage, or
            namespace prefix, in that order of preference, if available.

            :param concept_id: Concept identifier represented as a curie
            :param relation: SKOS mapping relationship, default is relatedMatch
            :return: Concept mapping for identifier
            """
            source = concept_id.split(":")[0]

            try:
                source = NamespacePrefix(source)
            except ValueError:
                try:
                    source = NamespacePrefix(source.upper())
                except ValueError as e:
                    err_msg = f"Namespace prefix not supported: {source}"
                    raise ValueError(err_msg) from e

            system = NAMESPACE_TO_SYSTEM_URI.get(source, source)

            return ConceptMapping(
                coding=Coding(code=code(concept_id), system=system), relation=relation
            )

        disease_obj = MappableConcept(
            id=f"normalize.disease.{record['concept_id']}",
            primaryCode=code(root=record["concept_id"]),
            conceptType="Disease",
            label=record["label"],
            extensions=[],
        )

        # mappings
        mappings = [
            _create_concept_mapping(record["concept_id"], relation=Relation.EXACT_MATCH)
        ]
        source_ids = record.get("xrefs", []) + record.get("associated_with", [])
        mappings.extend(_create_concept_mapping(source_id) for source_id in source_ids)
        if mappings:
            disease_obj.mappings = mappings

        for field in ("pediatric_disease", "oncologic_disease", "aliases"):
            value = record.get(field)
            if value is not None:
                disease_obj.extensions.append(Extension(name=field, value=value))

        response["match_type"] = match_type
        response["disease"] = disease_obj
        response = self._add_merged_meta(response)
        return NormalizationService(**response)

    def _record_order(self, record: dict) -> tuple[int, str]:
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
            _logger.warning("query.record_order: Invalid source name for %s", record)
            source_rank = 4
        return source_rank, record["concept_id"]

    def _handle_failed_merge_ref(
        self, record: dict, response: dict, query: str
    ) -> NormalizationService:
        """Log + fill out response for a failed merge reference lookup.

        :param Dict record: record containing failed merge_ref
        :param Dict response: in-progress response object
        :param str query: original query value
        :return: Normalized response with no match
        """
        _logger.error(
            "Merge ref lookup failed for ref %s in record %s from query %s",
            record["merge_ref"],
            record["concept_id"],
            query,
        )
        response["match_type"] = MatchType.NO_MATCH
        return NormalizationService(**response)

    def normalize(self, query: str) -> NormalizationService:
        """Return normalized concept for query.

        Use to retrieve normalized disease concept records:

        >>> from disease.query import QueryHandler
        >>> from disease.database import create_db
        >>> q = QueryHandler(create_db())
        >>> result = q.normalize("NSCLC")
        >>> result.disease.primaryCode.root
        'ncit:C2926'

        :param query: String to find normalized concept for
        :return: Normalized disease concept
        """
        # prepare basic response
        response = {
            "match_type": MatchType.NO_MATCH,
            "query": query,
            "warnings": self._emit_warnings(query),
            "service_meta_": ServiceMeta(
                version=__version__,
                response_datetime=datetime.datetime.now(tz=datetime.UTC),
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
                return self._add_disease(response, merge, MatchType.CONCEPT_ID)
            non_merged_match = (record, "concept_id")

        # check other match types
        for match_type in RefType:
            # get matches list for match tier
            matching_refs = self.db.get_refs_by_type(query_str, match_type)
            matching_records = [
                self.db.get_record_by_id(ref, False) for ref in matching_refs
            ]
            matching_records.sort(key=self._record_order)

            # attempt merge ref resolution until successful
            for match in matching_records:
                record = self.db.get_record_by_id(match["concept_id"], False)
                if record:
                    if "merge_ref" in record:
                        merge = self.db.get_record_by_id(
                            record["merge_ref"], case_sensitive=False, merge=True
                        )
                        if merge is None:
                            return self._handle_failed_merge_ref(
                                record, response, query_str
                            )
                        return self._add_disease(
                            response, merge, MatchType[match_type.upper()]
                        )
                    if not non_merged_match:
                        non_merged_match = (record, match_type)

        # if no successful match, try available non-merged match
        if non_merged_match:
            match_type = MatchType[non_merged_match[1].upper()]
            return self._add_disease(response, non_merged_match[0], match_type)

        return NormalizationService(**response)
