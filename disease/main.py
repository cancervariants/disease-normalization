"""Main application for FastAPI"""
from disease import __version__
from disease.query import QueryHandler, InvalidParameterException
from disease.schemas import SearchService, NormalizationService
from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.utils import get_openapi
import html
from typing import Optional


query_handler = QueryHandler()
app = FastAPI(docs_url='/disease', openapi_url='/disease/openapi.json')


def custom_openapi():
    """Generate custom fields for OpenAPI response"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="The VICC Disease Normalizer",
        version=__version__,
        openapi_version="3.0.3",
        description="Normalize disease terms.",
        routes=app.routes
    )
#    openapi_schema['info']['license'] = {  # TODO
#        "name": "Name-of-license",
#        "url": "http://www.to-be-determined.com"
#    }
    openapi_schema['info']['contact'] = {
        "name": "Alex H. Wagner",
        "email": "Alex.Wagner@nationwidechildrens.org"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# endpoint description text
get_matches_summary = ("Given query, provide highest matches from "
                       "each source.")
search_descr = "Search for disease term."
response_descr = "A response to a validly-formed query."
q_descr = "Disease term to search for."
keyed_descr = ("If true, return response as key-value pairs of "
               "sources to source matches. False by default")
incl_descr = ("Comma-separated list of source names to include in "
              "response. Will exclude all other sources. Will return HTTP "
              "status code 422: Unprocessable Entity if both 'incl' and "
              "'excl' parameters are given.")
excl_descr = ("Comma-separated list of source names to exclude in "
              "response. Will include all other sources. Will return HTTP "
              "status code 422: Unprocessable Entity if both 'incl' and"
              "'excl' parameters are given.")
normalize_description = ("Return merged strongest-match concept for query "
                         "string provided by user.")


@app.get("/disease/search",
         summary=get_matches_summary,
         description=search_descr,
         operation_id="getQueryResponse",
         response_description=response_descr,
         response_model=SearchService)
def search(q: str = Query(..., description=q_descr),
           keyed: Optional[bool] = Query(False, description=keyed_descr),
           incl: Optional[str] = Query('', description=incl_descr),
           excl: Optional[str] = Query('', description=excl_descr)):
    """For each source, return strongest-match concepts for query string
    provided by user.
    """
    try:
        response = query_handler.search_sources(html.unescape(q), keyed=keyed,
                                                incl=incl, excl=excl)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return response


merged_matches_summary = "Given query, provide normalized record."
merged_response_descr = "A response to a validly-formed query."
merged_q_descr = "Disease to normalize."


@app.get("/disease/normalize",
         summary=merged_matches_summary,
         operation_id="getQuerymergedResponse",
         response_description=merged_response_descr,
         response_model=NormalizationService,
         description=normalize_description)
def normalize(q: str = Query(..., description=merged_q_descr)):
    """Return strongest-match normalized concept for query string provided by
    user.
    :param q: therapy search term
    """
    try:
        response = query_handler.search_groups(q)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e))
    return response
