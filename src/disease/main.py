"""Main application for FastAPI"""

import html

from fastapi import FastAPI, HTTPException, Query
from fastapi.openapi.utils import get_openapi

from disease import __version__
from disease.database.database import create_db
from disease.query import InvalidParameterException, QueryHandler
from disease.schemas import NormalizationService, SearchService

db = create_db()
query_handler = QueryHandler(db)

app = FastAPI(
    docs_url="/disease",
    openapi_url="/disease/openapi.json",
    swagger_ui_parameters={"tryItOutEnabled": True},
)


def custom_openapi() -> dict | None:
    """Generate custom fields for OpenAPI response"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="The VICC Disease Normalizer",
        version=__version__,
        openapi_version="3.0.3",
        description="Normalize disease terms.",
        routes=app.routes,
    )
    #    openapi_schema['info']['license'] = {  # TODO
    #        "name": "Name-of-license",
    #        "url": "http://www.to-be-determined.com"
    #    }
    openapi_schema["info"]["contact"] = {
        "name": "Alex H. Wagner",
        "email": "Alex.Wagner@nationwidechildrens.org",
        "url": "https://www.nationwidechildrens.org/specialties/institute-for-genomic-medicine/research-labs/wagner-lab",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# endpoint description text
get_matches_summary = "Given query, provide highest matches from " "each source."
search_descr = "Search for disease term."
response_descr = "A response to a validly-formed query."
q_descr = "Disease term to search for."
incl_descr = (
    "Comma-separated list of source names to include in "
    "response. Will exclude all other sources. Will return HTTP "
    "status code 422: Unprocessable Entity if both 'incl' and "
    "'excl' parameters are given."
)
excl_descr = (
    "Comma-separated list of source names to exclude in "
    "response. Will include all other sources. Will return HTTP "
    "status code 422: Unprocessable Entity if both 'incl' and"
    "'excl' parameters are given."
)
normalize_description = (
    "Return merged strongest-match concept for query " "string provided by user."
)


@app.get(
    "/disease/search",
    summary=get_matches_summary,
    description=search_descr,
    operation_id="getQueryResponse",
    response_description=response_descr,
    response_model=SearchService,
    response_model_exclude_none=True,
)
def search(
    q: str = Query(..., description=q_descr),
    incl: str | None = Query("", description=incl_descr),
    excl: str | None = Query("", description=excl_descr),
) -> SearchService:
    """For each source, return strongest-match concepts for query string
    provided by user.

    :param q: disease search term
    :param incl: sources to include
    :param excl: sources to excl
    :return: search results
    """
    try:
        response = query_handler.search(html.unescape(q), incl=incl, excl=excl)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return response


merged_matches_summary = "Given query, provide normalized record."
merged_response_descr = "A response to a validly-formed query."
merged_q_descr = "Disease to normalize."


@app.get(
    "/disease/normalize",
    summary=merged_matches_summary,
    operation_id="getQuerymergedResponse",
    response_description=merged_response_descr,
    response_model=NormalizationService,
    description=normalize_description,
    response_model_exclude_none=True,
)
def normalize(q: str = Query(..., description=merged_q_descr)) -> NormalizationService:
    """Return strongest-match normalized concept for query string provided by
    user.
    :param q: disease search term
    """
    try:
        response = query_handler.normalize(q)
    except InvalidParameterException as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    return response
