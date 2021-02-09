"""This module provides methods for handling queries."""
import re
from typing import List, Dict, Set, Optional

from uvicorn.config import logger
from disease.database import Database
from disease.schemas import Disease, Meta, MatchType, SourceName, \
    NamespacePrefix, SourceIDAfterNamespace
from botocore.exceptions import ClientError

# use to fetch source name from schema based on concept id namespace
# e.g. {'ncit': 'NCIt'}
PREFIX_LOOKUP = {v.value: SourceName[k].value
                 for k, v in NamespacePrefix.__members__.items()
                 if k in SourceName.__members__.keys()}

# use to generate namespace prefix from source ID value
# e.g. {'c': 'NCIt'}
NAMESPACE_LOOKUP = {v.value.lower(): NamespacePrefix[k].value
                    for k, v in SourceIDAfterNamespace.__members__.items()
                    if v.value != ''}


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

    def _fetch_meta(self, src_name: str) -> Meta:
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
                response = Meta(**db_response['Item'])
                self.db.cached_sources[src_name] = response
                return response
            except ClientError as e:
                logger.error(e.response['Error']['Message'])

    def _add_record(self,
                    response: Dict[str, Dict],
                    item: Dict,
                    match_type: str) -> (Dict, str):
        """Add individual record to response object

        :param Dict[str, Dict] response: in-progress response object to return
            to client
        :param Dict item: Item retrieved from DynamoDB
        :param MatchType match_type: type of query match
        :return: Tuple containing updated response object, and string
            containing name of the source of the match
        """
        del item['label_and_type']
        attr_types = ['aliases', 'other_identifiers', 'xrefs']
        for attr_type in attr_types:
            if attr_type not in item.keys():
                item[attr_type] = []

        disease = Disease(**item)
        src_name = item['src_name']

        matches = response['source_matches']
        if src_name not in matches.keys():
            pass
        elif matches[src_name] is None:
            matches[src_name] = {
                'match_type': MatchType[match_type.upper()],
                'records': [disease],
                'meta_': self._fetch_meta(src_name)
            }
        elif matches[src_name]['match_type'] == MatchType[match_type.upper()]:
            matches[src_name]['records'].append(disease)

        return (response, src_name)

    def _fetch_records(self,
                       response: Dict[str, Dict],
                       concept_ids: Set[str],
                       match_type: str) -> (Dict, Set):
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
        return (response, matched_sources)

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
                    'meta_': self._fetch_meta(src_name)
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
            id_lookup = self.db.get_record_by_id(query, False)
            if id_lookup:
                concept_id_items += id_lookup
        for prefix in [p for p in NAMESPACE_LOOKUP.keys()
                       if query.startswith(p)]:
            concept_id = f'{NAMESPACE_LOOKUP[prefix]}:{query}'
            id_lookup = self.db.get_record_by_id(concept_id, False)
            if id_lookup:
                concept_id_items += id_lookup
        for item in concept_id_items:
            (resp, src_name) = self._add_record(resp, item,
                                                MatchType.CONCEPT_ID.name)
            sources = sources - {src_name}
        return (resp, sources)

    def _check_match_type(self,
                          query: str,
                          resp: Dict,
                          sources: Set[str],
                          match_type: str) -> (Dict, Set):
        """Check query for selected match type.
        :param str query: search string
        :param Dict resp: in-progress response object to return to client
        :param Set[str] sources: remaining unmatched sources
        :param str match_type: Match type to check for. Should be one of
            ['trade_name', 'label', 'alias']
        :return: Tuple with updated resp object and updated set of unmatched
                 sources
        """
        matches = self.db.get_records_by_type(query, match_type)
        if matches:
            concept_ids = {i['concept_id'] for i in matches}
            (resp, matched_srcs) = self._fetch_records(resp, concept_ids,
                                                       match_type)
            sources = sources - matched_srcs
        return (resp, sources)

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

        match_types = ['label', 'trade_name', 'alias']
        for match_type in match_types:
            (response, sources) = self._check_match_type(query, response,
                                                         sources, match_type)
            if len(sources) == 0:
                return response

        # remaining sources get no match
        return self._fill_no_matches(response)

    def _response_list(self, query: str, sources: List[str]) -> Dict:
        """Return response as list, where the first key-value in each item
        is the source name. Corresponds to `keyed=false` API parameter.

        :param str query: string to match against
        :param List[str] sources: sources to match from
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

    def search_sources(self, query_str, keyed=False, incl='', excl='') -> Dict:
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
        sources = {name.value.lower(): name.value for name in
                   SourceName.__members__.values()}

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

        return response