"""This module provides methods for handling queries."""
import re
from typing import Dict, Set, Optional, Tuple
from .version import __version__
from disease import NAMESPACE_LOOKUP, PREFIX_LOOKUP, SOURCES_LOWER_LOOKUP,\
    ITEM_TYPES, logger
from disease.database import Database
from disease.schemas import Disease, SourceMeta, MatchType, SourceName, \
    ServiceMeta, NormalizationService, SearchService
from botocore.exceptions import ClientError
from urllib.parse import quote
from datetime import datetime


class InvalidParameterException(Exception):
    """Exception for invalid parameter args provided by the user."""

    def __init__(self, message):
        """Create new instance
        :param str message: string describing the nature of the error
        """
        super().__init__(message)


class QueryHandler:
    """Class for normalizer management. Stores reference to database instance
    and normalizes query input.
    """

    def __init__(self, db_url: str = '', db_region: str = 'us-east-2'):
        """Initialize Normalizer instance.
        :param str db_url: URL to database source.
        :param str db_region: AWS default region.
        """
        self.db = Database(db_url=db_url, region_name=db_region)

    def _emit_warnings(self, query_str) -> Optional[Dict]:
        """Emit warnings if query contains non breaking space characters.
        :param str query_str: query string
        :return: dict keying warning type to warning description
        """
        warnings = None
        nbsp = re.search('\xa0|&nbsp;', query_str)
        if nbsp:
            warnings = {
                'nbsp': 'Query contains non breaking space characters.'
            }
            logger.warning(
                f'Query ({query_str}) contains non breaking space characters.'
            )
        return warnings

    def _fetch_meta(self, src_name: str) -> SourceMeta:
        """Fetch metadata for src_name.
        :param str src_name: name of source to get metadata for
        :return: Meta object containing source metadata
        """
        if src_name in self.db.cached_sources.keys():
            return self.db.cached_sources[src_name]
        else:
            try:
                db_response = self.db.metadata.get_item(
                    Key={'src_name': src_name}
                )
                response = SourceMeta(**db_response['Item'])
                self.db.cached_sources[src_name] = response
                return response
            except ClientError as e:
                logger.error(e.response['Error']['Message'])

    def _add_record(self,
                    response: Dict[str, Dict],
                    item: Dict,
                    match_type: str) -> Tuple[Dict, str]:
        """Add individual record to response object
        :param Dict[str, Dict] response: in-progress response object to return
            to client
        :param Dict item: Item retrieved from DynamoDB
        :param str match_type: type of query match
        :return: Tuple containing updated response object, and string
            containing name of the source of the match
        """
        del item['label_and_type']
        disease = Disease(**item)
        src_name = item['src_name']

        matches = response['source_matches']
        if src_name not in matches.keys():
            pass
        elif matches[src_name] is None:
            matches[src_name] = {
                'match_type': MatchType[match_type.upper()],
                'records': [disease],
                'source_meta_': self._fetch_meta(src_name)
            }
        elif matches[src_name]['match_type'] == MatchType[match_type.upper()]:
            matches[src_name]['records'].append(disease)

        return response, src_name

    def _fetch_records(self,
                       response: Dict[str, Dict],
                       concept_ids: Set[str],
                       match_type: str) -> Tuple[Dict, Set]:
        """Return matched Disease records as a structured response for a given
        collection of concept IDs.
        :param Dict[str, Dict] response: in-progress response object to return
            to client.
        :param List[str] concept_ids: List of concept IDs to build from.
            Should be all lower-case.
        :param str match_type: record should be assigned this type of
            match.
        :return: response Dict with records filled in via provided concept
            IDs, and Set of source names of matched records
        """
        matched_sources = set()
        for concept_id in concept_ids:
            try:
                match = self.db.get_record_by_id(concept_id.lower(),
                                                 case_sensitive=False)
                (response, src) = self._add_record(response, match, match_type)
                matched_sources.add(src)
            except ClientError as e:
                logger.error(e.response['Error']['Message'])
        return response, matched_sources

    def _fill_no_matches(self, resp: Dict[str, Dict]) -> Dict:
        """Fill all empty source_matches slots with NO_MATCH results.
        :param Dict[str, Dict] resp: incoming response object
        :return: response object with empty source slots filled with
                NO_MATCH results and corresponding source metadata
        """
        for src_name in resp['source_matches'].keys():
            if resp['source_matches'][src_name] is None:
                resp['source_matches'][src_name] = {
                    'match_type': MatchType.NO_MATCH,
                    'records': [],
                    'source_meta_': self._fetch_meta(src_name)
                }
        return resp

    def _check_concept_id(self,
                          query: str,
                          resp: Dict,
                          sources: Set[str]) -> (Dict, Set):
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
        for prefix in [p for p in NAMESPACE_LOOKUP.keys()
                       if query.startswith(p)]:
            concept_id = f'{NAMESPACE_LOOKUP[prefix]}:{query}'
            id_lookup = self.db.get_record_by_id(concept_id, False)
            if id_lookup:
                concept_id_items.append(id_lookup)
        for item in concept_id_items:
            (resp, src_name) = self._add_record(resp, item,
                                                MatchType.CONCEPT_ID.name)
            sources = sources - {src_name}
        return resp, sources

    def _check_match_type(self,
                          query: str,
                          resp: Dict,
                          sources: Set[str],
                          match_type: str) -> Tuple[Dict, Set]:
        """Check query for selected match type.
        :param str query: search string
        :param Dict resp: in-progress response object to return to client
        :param Set[str] sources: remaining unmatched sources
        :param str match_type: Match type to check for. Should be one of
            {'label', 'alias', 'xref', 'associated_with'}
        :return: Tuple with updated resp object and updated set of unmatched
                 sources
        """
        matches = self.db.get_records_by_type(query, match_type)
        if matches:
            concept_ids = {i['concept_id'] for i in matches}
            (resp, matched_srcs) = self._fetch_records(resp, concept_ids,
                                                       match_type)
            sources = sources - matched_srcs
        return resp, sources

    def _response_keyed(self, query: str, sources: Set[str]) -> Dict:
        """Return response as dict where key is source name and value
        is a list of records. Corresponds to `keyed=true` API parameter.
        :param str query: string to match against
        :param Set[str] sources: sources to match from
        :return: completed response object to return to client
        """
        response = {
            'query': query,
            'warnings': self._emit_warnings(query),
            'source_matches': {
                source: None for source in sources
            }
        }
        if query == '':
            response = self._fill_no_matches(response)
            return response
        query = query.lower()

        # check if concept ID match
        (response, sources) = self._check_concept_id(query, response, sources)
        if len(sources) == 0:
            return response

        for match_type in ITEM_TYPES.values():
            (response, sources) = self._check_match_type(query, response,
                                                         sources, match_type)
            if len(sources) == 0:
                return response

        # remaining sources get no match
        return self._fill_no_matches(response)

    def _response_list(self, query: str, sources: Set[str]) -> Dict:
        """Return response as list, where the first key-value in each item
        is the source name. Corresponds to `keyed=false` API parameter.
        :param str query: string to match against
        :param Set[str] sources: sources to match from
        :return: Completed response object to return to client
        """
        response_dict = self._response_keyed(query, sources)
        source_list = []
        for src_name in response_dict['source_matches'].keys():
            src = {
                "source": src_name,
            }
            to_merge = response_dict['source_matches'][src_name]
            src.update(to_merge)

            source_list.append(src)
        response_dict['source_matches'] = source_list

        return response_dict

    def search(self, query_str, keyed=False, incl="",
               excl="") -> SearchService:
        """Fetch normalized disease objects.
        :param str query_str: query, a string, to search for
        :param bool keyed: if true, return response as dict keying source names
            to source objects; otherwise, return list of source objects
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
            if self.db.metadata.get_item(Key={'src_name': v}).get('Item'):
                sources[k] = v
        if not incl and not excl:
            query_sources = set(sources.values())
        elif incl and excl:
            detail = "Cannot request both source inclusions and exclusions."
            raise InvalidParameterException(detail)
        elif incl:
            req_sources = [n.strip() for n in incl.split(',')]
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
            req_exclusions = [n.strip() for n in excl.lower().split(',')]
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

        if keyed:
            response = self._response_keyed(query_str, query_sources)
        else:
            response = self._response_list(query_str, query_sources)

        response['service_meta_'] = ServiceMeta(
            version=__version__,
            response_datetime=datetime.now(),
        ).dict()
        return SearchService(**response)

    def _add_merged_meta(self, response: Dict) -> Dict:
        """Add source metadata to response object.

        :param Dict response: in-progress response object
        :return: completed response object.
        """
        sources_meta = {}
        vod = response['disease_descriptor']
        ids = [vod['disease_id']] + vod.get('xrefs', [])
        for concept_id in ids:
            prefix = concept_id.split(':')[0]
            src_name = PREFIX_LOOKUP[prefix.lower()]
            if src_name not in sources_meta:
                sources_meta[src_name] = self._fetch_meta(src_name)
        response['source_meta_'] = sources_meta
        return response

    def _add_vod(self, response: Dict, record: Dict, query: str,
                 match_type: MatchType) -> NormalizationService:
        """Format received DB record as VOD and update response object.

        :param Dict response: in-progress response object
        :param Dict record: record as stored in DB
        :param str query: query string from user request
        :param MatchType match_type: type of match achieved
        :return: completed normalized response object ready to return to user
        """
        vod = {
            'id': f'normalize.disease:{quote(query)}',
            'type': 'DiseaseDescriptor',
            'disease_id': record['concept_id'],
            'label': record['label'],
            'extensions': [],
        }
        if 'xrefs' in record:
            vod['xrefs'] = record['xrefs']
        if 'aliases' in record:
            vod['alternate_labels'] = record['aliases']
        if 'pediatric_disease' in record and \
                record['pediatric_disease'] is not None:
            vod['extensions'].append({
                'type': 'Extension',
                'name': 'pediatric_disease',
                'value': record['pediatric_disease']
            })
        if 'associated_with' in record and record['associated_with']:
            vod['extensions'].append({
                'type': 'Extension',
                'name': 'associated_with',
                'value': record['associated_with']
            })
        if not vod['extensions']:
            del vod['extensions']
        response['match_type'] = match_type
        response['disease_descriptor'] = vod
        response = self._add_merged_meta(response)
        return NormalizationService(**response)

    def _record_order(self, record: Dict) -> (int, str):
        """Construct priority order for matching. Only called by sort().

        :param Dict record: individual record item in iterable to sort
        :return: tuple with rank value and concept ID
        """
        src = record['src_name']
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
            logger.warning(f"query.record_order: Invalid source name for "
                           f"{record}")
            source_rank = 4
        return source_rank, record['concept_id']

    def _handle_failed_merge_ref(self, record, response,
                                 query) -> NormalizationService:
        """Log + fill out response for a failed merge reference lookup.

        :param Dict record: record containing failed merge_ref
        :param Dict response: in-progress response object
        :param str query: original query value
        :return: Normalized response with no match
        """
        logger.error(f"Merge ref lookup failed for ref {record['merge_ref']} "
                     f"in record {record['concept_id']} from query {query}")
        response['match_type'] = MatchType.NO_MATCH
        return NormalizationService(**response)

    def normalize(self, query: str) -> NormalizationService:
        """Return normalized concept for given search term.
        :param str query: string to search against
        :return: NormalizationService object with complete response
        """
        # prepare basic response
        response = {
            'query': query,
            'warnings': self._emit_warnings(query),
            'service_meta_': ServiceMeta(
                version=__version__,
                response_datetime=datetime.now(),
            )
        }
        if query == '':
            response['match_type'] = MatchType.NO_MATCH
            return NormalizationService(**response)
        query_str = query.lower().strip()

        # check merged concept ID match
        record = self.db.get_record_by_id(query_str, case_sensitive=False,
                                          merge=True)
        if record:
            return self._add_vod(response, record, query, MatchType.CONCEPT_ID)

        non_merged_match = None

        # check concept ID match
        record = self.db.get_record_by_id(query_str, case_sensitive=False)
        if record:
            if 'merge_ref' in record:
                merge = self.db.get_record_by_id(record['merge_ref'],
                                                 case_sensitive=False,
                                                 merge=True)
                if merge is None:
                    return self._handle_failed_merge_ref(record, response,
                                                         query_str)
                else:
                    return self._add_vod(response, merge, query,
                                         MatchType.CONCEPT_ID)
            else:
                non_merged_match = (record, 'concept_id')

        # check other match types
        for match_type in ['label', 'alias', 'xref', 'associated_with']:
            # get matches list for match tier
            query_matches = self.db.get_records_by_type(query_str, match_type)
            query_matches = [self.db.get_record_by_id(m['concept_id'],
                                                      case_sensitive=False)
                             for m in query_matches]
            query_matches.sort(key=self._record_order)

            # attempt merge ref resolution until successful
            for match in query_matches:
                record = self.db.get_record_by_id(match['concept_id'], False)
                if record:
                    if 'merge_ref' in record:
                        merge = self.db.get_record_by_id(record['merge_ref'],
                                                         case_sensitive=False,
                                                         merge=True)
                        if merge is None:
                            return self._handle_failed_merge_ref(record,
                                                                 response,
                                                                 query_str)
                        else:
                            return self._add_vod(response, merge, query,
                                                 MatchType[match_type.upper()])
                    else:
                        if not non_merged_match:
                            non_merged_match = (record, match_type)

        # if no successful match, try available non-merged match
        if non_merged_match:
            match_type = MatchType[non_merged_match[1].upper()]
            return self._add_vod(response, non_merged_match[0], query,
                                 match_type)

        if not query_matches:
            response['match_type'] = MatchType.NO_MATCH
        return NormalizationService(**response)
